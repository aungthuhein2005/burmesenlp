"""Tests for the BMWE (Burmese Multi-Word Expression) engine."""

from __future__ import annotations

import json

import pytest

from burmesenlp import BMWEEngine, BurmeseNLP, MWEEntry, MWEToken, process
from burmesenlp.lexicon import Lexicon
from burmesenlp.mwe.loader import (
    cache_path_for,
    expression_to_tokens,
    infer_category,
    load_entries,
    try_load_cache,
)
from burmesenlp.mwe.matcher import choose
from burmesenlp.mwe.trie import MWETrie
from burmesenlp.mwe.validator import AcceptAllValidator


@pytest.fixture
def empty_engine():
    return BMWEEngine(lexicon=Lexicon.default(), autoload_idioms=False)


@pytest.fixture(scope="module")
def lexicon():
    return Lexicon.default()


def test_empty_input(empty_engine):
    assert empty_engine.process([]) == []
    merged, spans = empty_engine.process_detailed([])
    assert merged == []
    assert spans == []


def test_no_match_passthrough(empty_engine):
    tokens = ["စာ", "ဖတ်", "သည်"]
    assert empty_engine.process(tokens) == tokens


def test_longest_match_wins(empty_engine):
    short = MWEEntry("က ခ", ("က", "ခ"), "MWE", priority=0)
    long = MWEEntry("က ခ ဂ", ("က", "ခ", "ဂ"), "MWE", priority=0)
    empty_engine._trie.insert(short)
    empty_engine._trie.insert(long)
    assert empty_engine.process(["က", "ခ", "ဂ", "ဃ"]) == ["ကခဂ", "ဃ"]


def test_priority_beats_length(empty_engine):
    short = MWEEntry("က ခ", ("က", "ခ"), "MWE", priority=10)
    long = MWEEntry("က ခ ဂ", ("က", "ခ", "ဂ"), "MWE", priority=0)
    empty_engine._trie.insert(long)
    empty_engine._trie.insert(short)
    assert empty_engine.process(["က", "ခ", "ဂ"]) == ["ကခ", "ဂ"]


def test_overlapping_left_to_right_greedy(empty_engine):
    empty_engine._trie.insert(MWEEntry("က ခ", ("က", "ခ"), "MWE"))
    empty_engine._trie.insert(MWEEntry("ခ ဂ", ("ခ", "ဂ"), "MWE"))
    assert empty_engine.process(["က", "ခ", "ဂ"]) == ["ကခ", "ဂ"]


def test_choose_priority_then_length():
    a = MWEEntry("a", ("x", "y"), "MWE", priority=1)
    b = MWEEntry("b", ("x", "y", "z"), "MWE", priority=0)
    assert choose([a, b]) is a
    c = MWEEntry("c", ("x", "y"), "MWE", priority=0)
    d = MWEEntry("d", ("x", "y", "z"), "MWE", priority=0)
    assert choose([c, d]) is d


def test_punctuation_untouched(empty_engine):
    empty_engine._trie.insert(MWEEntry("စာ ဖတ်", ("စာ", "ဖတ်"), "IDIOM"))
    tokens = ["စာ", "ဖတ်", "။"]
    assert empty_engine.process(tokens) == ["စာဖတ်", "။"]


def test_multiple_mwes_in_one_sentence(empty_engine):
    empty_engine._trie.insert(MWEEntry("က ခ", ("က", "ခ"), "MWE"))
    empty_engine._trie.insert(MWEEntry("ဂ ဃ", ("ဂ", "ဃ"), "MWE"))
    assert empty_engine.process(["က", "ခ", "နှင့်", "ဂ", "ဃ"]) == [
        "ကခ",
        "နှင့်",
        "ဂဃ",
    ]


def test_duplicate_entries_deduped(tmp_path, empty_engine):
    path = tmp_path / "dup.txt"
    path.write_text("hello world\nhello world\n", encoding="utf-8")
    n = empty_engine.load(
        str(path), category="MWE", priority=0, write_cache_on_miss=False
    )
    assert n == 1


def test_organization_category_from_path(tmp_path, lexicon):
    org_dir = tmp_path / "organization"
    org_dir.mkdir()
    path = org_dir / "orgs.txt"
    path.write_text("United Nations\nWorld Bank\n", encoding="utf-8")
    assert infer_category(str(path)) == "ORGANIZATION"
    entries = load_entries(
        str(path), lexicon, use_cache=False, write_cache_on_miss=False
    )
    assert entries
    assert all(e.category == "ORGANIZATION" for e in entries)


def test_spacing_variants_same_tokens(lexicon):
    variants = [
        "အိတ်ပေါက်နှင့် ဖားကောက်",
        "အိတ်ပေါက်နှင့်ဖားကောက်",
        "အိတ်ပေါက် နှင့် ဖားကောက်",
    ]
    seqs = [expression_to_tokens(v, lexicon) for v in variants]
    assert seqs[0] == ("အိတ်", "ပေါက်", "နှင့်", "ဖား", "ကောက်")
    assert seqs[0] == seqs[1] == seqs[2]


def test_loader_matches_pipeline_word_segment(lexicon):
    """BMWE load tokens must equal BurmeseNLP.word_segment on the same string."""
    nlp = BurmeseNLP(gazetteer=False)
    expr = "အိတ်ပေါက်နှင့် ဖားကောက်"
    assert expression_to_tokens(expr, nlp.lexicon) == tuple(nlp.word_segment(expr))


def test_idiom_merges_after_word_tokenize(empty_engine, lexicon):
    expr = "အိတ်ပေါက်နှင့် ဖားကောက်"
    toks = expression_to_tokens(expr, lexicon)
    empty_engine._trie.insert(
        MWEEntry(expr, toks, "IDIOM"),
    )
    # Runtime sentence tokenized the same way
    runtime = ["ဒီ", "ကောင်", *toks, "နေ", "တာ", "ပါ", "ကွာ"]
    merged, spans = empty_engine.process_detailed(runtime)
    assert spans
    assert spans[0].tokens == toks
    assert spans[0].category == "IDIOM"
    assert "အိတ်ပေါက်နှင့်ဖားကောက်" in merged or "".join(toks) in merged


def test_real_idioms_match_user_sentence():
    nlp = BurmeseNLP(gazetteer=False)
    text = "ဒီကောင် အိတ်ပေါက်နှင့် ဖားကောက် နေတာပါကွာ"
    doc = nlp.process(text)
    assert any(m.category == "IDIOM" for m in doc.mwe)
    idiom = next(m for m in doc.mwe if m.category == "IDIOM")
    assert idiom.resolved_pos() == "IDIOM"
    assert idiom.index is not None
    assert doc.pos_tags[idiom.index][1] == "IDIOM"
    assert doc.words[idiom.index] == idiom.text
    assert len(doc.pos_tags) == len(doc.words)
    # Chunker should treat IDIOM as a fixed expression
    assert any(
        c.type.value == "FIXED_EXPRESSION" and idiom.text in c.text
        for c in doc.chunks
    )


def test_mwe_pos_override_on_tagger(empty_engine, lexicon):
    from burmesenlp.tag.rule import POSTagger

    toks = ("အိတ်", "ပေါက်", "နှင့်", "ဖား", "ကောက်")
    empty_engine._trie.insert(MWEEntry("x", toks, "IDIOM", pos="IDIOM"))
    merged, spans = empty_engine.process_detailed(list(toks))
    tags = POSTagger(lexicon).tag(merged, mwe=spans)
    assert tags[0][1] == "IDIOM"



def test_cache_roundtrip(tmp_path, lexicon):
    source = tmp_path / "idioms.json"
    source.write_text(
        json.dumps(["အိတ်ပေါက်နှင့် ဖားကောက်", "ကံတူ အကျိုးပေး"], ensure_ascii=False),
        encoding="utf-8",
    )
    entries = load_entries(
        str(source),
        lexicon,
        category="IDIOM",
        use_cache=False,
        write_cache_on_miss=True,
    )
    cpath = cache_path_for(source)
    assert cpath.is_file()
    assert len(entries) >= 1

    cached = try_load_cache(source, lexicon, category="IDIOM")
    assert cached is not None
    assert {e.tokens for e in cached} == {e.tokens for e in entries}

    # Fresh load should hit cache (same fingerprints)
    again = load_entries(str(source), lexicon, category="IDIOM", use_cache=True)
    assert {e.tokens for e in again} == {e.tokens for e in entries}


def test_cache_stale_when_source_changes(tmp_path, lexicon):
    source = tmp_path / "idioms.json"
    source.write_text(json.dumps(["hello world"], ensure_ascii=False), encoding="utf-8")
    load_entries(
        str(source), lexicon, use_cache=False, write_cache_on_miss=True
    )
    source.write_text(
        json.dumps(["hello world", "foo bar"], ensure_ascii=False),
        encoding="utf-8",
    )
    assert try_load_cache(source, lexicon, category="MWE") is None


def test_validator_reject(empty_engine):
    class RejectAll:
        def validate(self, entry, context_tokens, start):
            return False

    empty_engine._validator = RejectAll()
    empty_engine._trie.insert(MWEEntry("က ခ", ("က", "ခ"), "MWE"))
    assert empty_engine.process(["က", "ခ"]) == ["က", "ခ"]


def test_accept_all_validator():
    v = AcceptAllValidator()
    e = MWEEntry("a b", ("a", "b"), "MWE")
    assert v.validate(e, ["a", "b"], 0) is True


def test_trie_search_collects_all_lengths():
    trie = MWETrie()
    trie.insert(MWEEntry("a b", ("a", "b"), "MWE"))
    trie.insert(MWEEntry("a b c", ("a", "b", "c"), "MWE"))
    hits = trie.search(["a", "b", "c", "d"], 0)
    assert len(hits) == 2


def test_public_exports():
    assert BMWEEngine is not None
    assert MWEEntry is not None
    assert MWEToken is not None
    doc = process("စာ။", gazetteer=False)
    assert hasattr(doc, "mwe")
