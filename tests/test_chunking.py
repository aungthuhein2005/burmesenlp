"""Tests for YAML-driven phrase chunking."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from burmesenlp import BurmeseNLP, ChunkType, Document, chunk, chunk_from_tokens, process
from burmesenlp.chunking.chunker import PhraseChunker
from burmesenlp.chunking.clause import ClauseParser
from burmesenlp.chunking.matcher import compile_pattern, normalize_pattern
from burmesenlp.chunking.models import (
    ROLE_HEAD_NOUN,
    ROLE_RELATIVE_MODIFIER,
    ClauseType,
    GrammarError,
)
from burmesenlp.chunking.rules import (
    CompiledGrammar,
    load_all_rules,
    load_aliases,
    load_clause_rules,
    load_exceptions,
    load_markers,
    load_phrase_rules,
    load_postposition_roles,
    reload_default_grammar,
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


def test_clause_rules_yaml_loads():
    reload_default_grammar()
    rules = load_clause_rules()
    texts = set(rules.marker_texts())
    assert "သော" in texts
    assert "လျှင်" in texts
    assert "ကြောင့်" in texts
    assert "သည်" in rules.sentence_end
    assert "conditional" in rules.kinds
    assert rules.kind("purpose") is not None


def test_postposition_roles_yaml():
    roles = load_postposition_roles()
    ko = roles.get("ကို")
    assert ko is not None
    assert ko.default_role == "OBJECT"
    assert "GOAL" in ko.possible_roles


def test_conditional_and_main_clauses():
    words = ["မိုး", "ရွာ", "လျှင်", "အိမ်", "မှာ", "နေ", "မည်", "။"]
    tags = ["NOUN", "VERB", "PART", "NOUN", "POSTP", "VERB", "SFP", "PUNCT"]
    phrases = chunk_from_tokens(words, tags)
    tree = ClauseParser().parse_window(phrases, words=words)
    types = [c.type for c in tree.clauses]
    assert ClauseType.CONDITIONAL in types
    assert ClauseType.MAIN in types
    cond = next(c for c in tree.clauses if c.type == ClauseType.CONDITIONAL)
    assert cond.phrases  # built from phrases, not bare words
    assert any(p.type == ChunkType.VERB_PHRASE for p in cond.phrases)


def test_relative_nests_inside_np():
    """Relative is NOT a top-level clause — it nests under NP."""
    words = ["လိုအပ်", "သော", "စာအုပ်"]
    tags = ["VERB", "PART", "NOUN"]
    phrases = chunk_from_tokens(words, tags)
    tree = ClauseParser().parse_window(phrases, words=words)
    assert all(c.type != ClauseType.RELATIVE for c in tree.clauses)
    nested = [p for p in tree.phrases if p.children]
    assert nested
    roles = {ch.role for ch in nested[0].children}
    assert ROLE_RELATIVE_MODIFIER in roles
    assert ROLE_HEAD_NOUN in roles


def test_reason_clause():
    words = ["မိုး", "ရွာ", "သောကြောင့်", "မ", "သွား", "ဘူး", "။"]
    tags = ["NOUN", "VERB", "PART", "PART", "VERB", "PART", "PUNCT"]
    phrases = chunk_from_tokens(words, tags)
    tree = ClauseParser().parse_window(phrases, words=words)
    assert any(c.type == ClauseType.REASON for c in tree.clauses)
    assert any(c.type == ClauseType.MAIN for c in tree.clauses)


def test_purpose_clause_vs_purpose_vp():
    # NP + VP + ရန် → PURPOSE clause
    words_clause = ["စာ", "ဖတ်", "ရန်"]
    tags_clause = ["NOUN", "VERB", "PART"]
    tree_c = ClauseParser().parse_window(
        chunk_from_tokens(words_clause, tags_clause), words=words_clause
    )
    assert any(c.type == ClauseType.PURPOSE for c in tree_c.clauses)

    # bare VP + ရန် → Purpose VP (not a PURPOSE clause)
    words_vp = ["ဖတ်", "ရန်"]
    tags_vp = ["VERB", "PART"]
    tree_v = ClauseParser().parse_window(
        chunk_from_tokens(words_vp, tags_vp), words=words_vp
    )
    assert not any(c.type == ClauseType.PURPOSE for c in tree_v.clauses)
    assert any(p.role == "PurposeVP" for p in tree_v.phrases)


def test_vp_merges_negation_shell():
    chunks = chunk_from_tokens(
        ["မ", "သွား", "ဘူး"],
        ["PART", "VERB", "PART"],
    )
    vps = [c for c in chunks if c.type == ChunkType.VERB_PHRASE]
    assert vps
    assert vps[0].tokens == ["မ", "သွား", "ဘူး"]


def test_vp_merges_aspect_particles():
    chunks = chunk_from_tokens(
        ["ဖတ်", "နေ", "သည်"],
        ["VERB", "AUX", "SFP"],
    )
    vps = [c for c in chunks if c.type == ChunkType.VERB_PHRASE]
    assert vps
    assert vps[0].tokens == ["ဖတ်", "နေ", "သည်"]


def test_simple_sentence_is_main_clause():
    words = ["ကျွန်တော်", "စာ", "ဖတ်", "နေ", "သည်", "။"]
    tags = ["PRON", "NOUN", "VERB", "AUX", "SFP", "PUNCT"]
    tree = ClauseParser().parse_window(
        chunk_from_tokens(words, tags), words=words
    )
    assert len(tree.clauses) == 1
    assert tree.clauses[0].type == ClauseType.MAIN


def test_pp_gets_default_semantic_role():
    words = ["ရန်ကုန်", "ကို", "သွား", "သည်"]
    tags = ["NOUN", "POSTP", "VERB", "SFP"]
    tree = ClauseParser().parse_window(
        chunk_from_tokens(words, tags), words=words
    )
    pps = [p for p in tree.phrases if p.type == ChunkType.POSTPOSITIONAL_PHRASE]
    assert pps
    assert pps[0].semantic_role == "OBJECT"
    assert pps[0].grammatical_function == "OBJECT"


def test_clause_scoped_to_pipeline_sentences():
    text = (
        "နံပါတ်စဉ်အရ G ဖြစ်သောအဆောင်မို့ဂျီဟောပဟုအခေါ်များလေသည်။"
        "ဘယ်သူကဘယ်လိုစလိုက်သည်ကိုတော့အသေအချာမသိရချေ။"
        "ဂျီဟာကိုပမာခိုင်းရလျှင်"
    )
    doc = process(text, gazetteer=False)
    assert len(doc.sentences) >= 2
    assert doc.sentence_trees
    assert len(doc.sentence_trees) == len(doc.sentences)
    for tree in doc.sentence_trees:
        for clause in tree.clauses:
            assert clause.type != ClauseType.RELATIVE
            assert clause.phrases
            assert clause.text.count("။") <= 1


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
    doc = process("ကျွန်တော်ကျောင်းသို့သွားသည်။", gazetteer=False)
    assert isinstance(doc, Document)
    assert doc.words
    assert doc.pos_tags
    assert "chunks" in doc
    assert doc["chunks"] is doc.chunks
    assert isinstance(doc.chunks, list)
    nlp = BurmeseNLP(gazetteer=False)
    assert doc.pos_tags == nlp.pos_tag(doc.words)
    payload = doc.to_dict()
    json.dumps(payload, ensure_ascii=False)


def test_maximal_munch_prefers_longer_span():
    """Length beats shorter alternatives at the same start index."""
    # PP can cover NOUN NOUN POSTP (len 3); NP can cover NOUN NOUN (len 2).
    # Length-primary → full PP. Priority-primary would still pick PP here, but
    # this asserts the longer span is chosen.
    chunks = chunk_from_tokens(
        ["မန္တလေး", "ပွဲ", "က"],
        ["NOUN", "NOUN", "POSTP"],
    )
    pps = [c for c in chunks if c.type == ChunkType.POSTPOSITIONAL_PHRASE]
    assert pps
    assert pps[0].tokens == ["မန္တလေး", "ပွဲ", "က"]


def test_equal_length_uses_priority():
    """When spans are equal length, higher priority wins (NP over NUMP)."""
    chunks = chunk_from_tokens(["နှစ်", "ယောက်"], ["NUM", "NOUN"])
    # Both NP and NUMP match length 2; NP priority 100 > NUMP 70.
    assert any(c.type == ChunkType.NOUN_PHRASE for c in chunks)


def test_chunk_text_api_unicode():
    result = chunk("စာဖတ်သည်", use_gazetteer=False)
    assert isinstance(result, list)
    assert any(c.type == ChunkType.VERB_PHRASE for c in result) or result == []


def test_default_grammar_loads():
    from burmesenlp.chunking.rules import reload_default_grammar, load_clause_rules

    reload_default_grammar()
    rules = load_all_rules()
    assert any(r.type == ChunkType.VERB_PHRASE for r in rules)
    assert not any(r.type == ChunkType.CLAUSE for r in rules)
    assert load_aliases()["PROPN"] == frozenset({"NOUN"})
    g = CompiledGrammar.from_rules(rules, load_aliases())
    assert g.pattern_rules
    # Typed clauses live in clause_rules.yml (not phrase_rules CLAUSE stubs)
    cr = load_clause_rules()
    assert "လျှင်" in cr.marker_texts()
    assert cr.kind("conditional") is not None
