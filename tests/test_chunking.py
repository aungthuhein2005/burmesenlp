"""Tests for YAML-driven phrase chunking."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from burmesenlp import BurmeseNLP, ChunkType, Document, chunk, chunk_from_tokens, process
from burmesenlp.chunking.chunker import PhraseChunker
from burmesenlp.chunking.matcher import compile_pattern, normalize_pattern
from burmesenlp.chunking.models import GrammarError
from burmesenlp.chunking.rules import (
    CompiledGrammar,
    load_all_rules,
    load_aliases,
    load_exceptions,
    load_markers,
    load_phrase_rules,
)


def test_empty_input():
    assert chunk_from_tokens([], []) == []


def test_length_mismatch_raises():
    with pytest.raises(ValueError, match="mismatch"):
        chunk_from_tokens(["a"], ["NOUN", "VERB"])


def test_punctuation_only_skipped_or_empty():
    chunks = chunk_from_tokens(["။"], ["PUNCT"])
    assert all(c.type != ChunkType.VERB_PHRASE for c in chunks)


def test_matcher_optional_star_plus_and_alternatives():
    pat = compile_pattern("ADV? VERB AUX* SFP?")
    words = ["ပို", "လုပ်", "ထား", "တယ်"]
    tags = ["ADV", "VERB", "AUX", "SFP"]
    assert pat.match_at(words, tags, 0) == 4

    pat2 = compile_pattern("(NOUN|PRON)+")
    assert pat2.match_at(["သူ", "စာ"], ["PRON", "NOUN"], 0) == 2


def test_list_pattern_normalizes_to_dsl():
    assert normalize_pattern(["VERB", "AUX*", "SFP?"]) == "VERB AUX* SFP?"


def test_propn_alias_matches_noun():
    pat = compile_pattern("(PROPN)+ POSTP")
    assert pat.match_at(["ရန်ကုန်", "ကို"], ["NOUN", "POSTP"], 0) == 2


def test_noun_phrase():
    chunks = chunk_from_tokens(
        ["ကောင်း", "စာ"],
        ["ADJ", "NOUN"],
    )
    nps = [c for c in chunks if c.type == ChunkType.NOUN_PHRASE]
    assert nps
    assert nps[0].tokens == ["ကောင်း", "စာ"]
    assert nps[0].text == "ကောင်းစာ"


def test_verb_phrase_with_aux_sfp():
    chunks = chunk_from_tokens(
        ["ခံစား", "နေ", "တယ်"],
        ["VERB", "AUX", "SFP"],
    )
    vps = [c for c in chunks if c.type == ChunkType.VERB_PHRASE]
    assert len(vps) == 1
    assert vps[0].tokens == ["ခံစား", "နေ", "တယ်"]


def test_verb_phrase_negation():
    chunks = chunk_from_tokens(
        ["မ", "သွား", "ဘူး"],
        ["PART", "VERB", "PART"],
    )
    vps = [c for c in chunks if c.type == ChunkType.VERB_PHRASE]
    assert vps
    assert vps[0].tokens[0] == "မ"
    assert "သွား" in vps[0].tokens


def test_postpositional_phrase():
    chunks = chunk_from_tokens(
        ["ရန်ကုန်", "ကို"],
        ["NOUN", "POSTP"],
    )
    pps = [c for c in chunks if c.type == ChunkType.POSTPOSITIONAL_PHRASE]
    assert len(pps) == 1
    assert pps[0].text == "ရန်ကုန်ကို"


def test_pp_with_compound_noun():
    chunks = chunk_from_tokens(
        ["မန္တလေး", "ပွဲ", "က"],
        ["NOUN", "NOUN", "POSTP"],
    )
    pps = [c for c in chunks if c.type == ChunkType.POSTPOSITIONAL_PHRASE]
    assert pps
    assert pps[0].tokens == ["မန္တလေး", "ပွဲ", "က"]


def test_adjective_and_numeral_phrases():
    adj = chunk_from_tokens(["အရမ်း", "ကောင်း"], ["ADV", "ADJ"])
    assert any(c.type == ChunkType.ADJECTIVE_PHRASE for c in adj)

    num = chunk_from_tokens(["နှစ်", "ယောက်"], ["NUM", "NOUN"])
    assert any(
        c.type in (ChunkType.NUMERAL_PHRASE, ChunkType.NOUN_PHRASE) for c in num
    )


def test_multi_chunk_sentence_pp_and_vp():
    chunks = chunk_from_tokens(
        ["ရန်ကုန်", "ကို", "သွား", "သည်"],
        ["NOUN", "POSTP", "VERB", "SFP"],
    )
    assert any(c.type == ChunkType.POSTPOSITIONAL_PHRASE for c in chunks)
    assert any(c.type == ChunkType.VERB_PHRASE for c in chunks)


def test_clause_split_on_markers():
    chunks = chunk_from_tokens(
        ["သွား", "ပြီး", "လာ", "သည်"],
        ["VERB", "PART", "VERB", "SFP"],
    )
    clauses = [c for c in chunks if c.type == ChunkType.CLAUSE]
    assert len(clauses) >= 2
    assert "ပြီး" in clauses[0].tokens


def test_fixed_expression_exception():
    ch = PhraseChunker()
    assert ch._match_joined_text(["မင်္ဂလာ", "ပါ"], 0, "မင်္ဂလာပါ") == 2
    out = chunk_from_tokens(["မင်္ဂလာ", "ပါ"], ["NOUN", "PART"])
    assert any(c.type == ChunkType.GREETING for c in out)


def test_pos_tags_accepted_as_pairs():
    chunks = chunk_from_tokens(
        ["စာ", "ဖတ်"],
        [("စာ", "NOUN"), ("ဖတ်", "VERB")],
    )
    assert chunks


def test_chunking_does_not_mutate_pos():
    words = ["သွား", "သည်"]
    tags = ["VERB", "SFP"]
    original = list(tags)
    chunk_from_tokens(words, tags)
    assert tags == original


def test_invalid_pattern_raises():
    with pytest.raises(GrammarError):
        compile_pattern("!!!")


def test_invalid_yaml_phrase_raises(tmp_path: Path):
    bad = tmp_path / "phrase_rules.yml"
    bad.write_text(
        "phrases:\n  - name: x\n    type: NOPE\n    priority: 1\n    patterns:\n      - [NOUN]\n",
        encoding="utf-8",
    )
    with pytest.raises(GrammarError, match="invalid type"):
        load_phrase_rules(bad)


def test_markers_and_exceptions_load():
    markers = load_markers()
    assert "ကို" in markers.noun_phrase_end["object"]
    assert "ပြီး" in markers.all_clause_markers()
    exc = load_exceptions()
    assert "ရန်ကုန်" in exc.never_split
    assert any(t == "မင်္ဂလာပါ" for t, _ in exc.special_phrases)


def test_process_returns_document_with_chunks():
    doc = process("ကျွန်တော်ကျောင်းသို့သွားသည်။")
    assert isinstance(doc, Document)
    assert doc.words
    assert doc.pos_tags
    assert "chunks" in doc
    assert doc["chunks"] is doc.chunks
    assert isinstance(doc.chunks, list)
    nlp = BurmeseNLP()
    assert doc.pos_tags == nlp.pos_tag(doc.words)
    payload = doc.to_dict()
    json.dumps(payload, ensure_ascii=False)


def test_chunk_text_api_unicode():
    result = chunk("စာဖတ်သည်")
    assert isinstance(result, list)
    assert any(c.type == ChunkType.VERB_PHRASE for c in result) or result == []


def test_default_grammar_loads():
    rules = load_all_rules()
    assert any(r.type == ChunkType.VERB_PHRASE for r in rules)
    assert load_aliases()["PROPN"] == frozenset({"NOUN"})
    g = CompiledGrammar.from_rules(rules, load_aliases())
    assert g.pattern_rules
