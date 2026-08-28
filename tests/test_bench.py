"""bench module: pure-function unit tests (no network) + an opt-in
integration test that actually downloads myPOS (BURMESENLP_BENCH_TEST=1)."""

from __future__ import annotations

import os

import pytest

from burmesenlp.bench.audit import Disagreement, categorize, find_disagreements, sample_diverse
from burmesenlp.bench.boundaries import (
    BoundaryCounts,
    canonical_reference_text,
    canonical_word_boundaries,
    score_corpus,
    score_corpus_stratified,
    word_boundaries,
)
from burmesenlp.bench.corpora import (
    GoldSentence,
    _parse_alt_line,
    _parse_line_nopipe,
    _parse_line_pipe,
)
from burmesenlp.bench.diff import diff_spans, load_external_segmentation


def test_word_boundaries_basic():
    assert word_boundaries(["ab", "cd", "e"]) == {2, 4}
    assert word_boundaries(["single"]) == set()
    assert word_boundaries([]) == set()


def test_canonical_reference_text_and_boundaries_agree():
    words = ["ab", "cd"]
    text = canonical_reference_text(words)
    assert text == "abcd"
    assert canonical_word_boundaries(words) == {2}


def test_canonical_reference_text_applies_canonical_order():
    # medial ya then medial wa (canonical order) vs the swapped-key variant
    canon = "ကျွ"
    swapped = "ကွျ"
    assert canonical_reference_text([swapped]) == canonical_reference_text([canon])


def test_boundary_counts_precision_recall_f1():
    counts = BoundaryCounts()
    counts.add(hyp={1, 2, 3}, gold={1, 2, 4})
    assert counts.tp == 2
    assert counts.fp == 1
    assert counts.fn == 1
    assert counts.precision == pytest.approx(2 / 3)
    assert counts.recall == pytest.approx(2 / 3)
    assert counts.f1 == pytest.approx(2 / 3)


def test_boundary_counts_empty_is_zero_not_error():
    counts = BoundaryCounts()
    assert counts.precision == 0.0
    assert counts.recall == 0.0
    assert counts.f1 == 0.0


def test_score_corpus_perfect_segmenter():
    gold = [["ab", "cd"], ["e", "fg", "h"]]

    def perfect(text):
        # cheat: reconstruct from a lookup, proving the harness scores
        # whatever segment_fn returns against the true gold boundaries
        mapping = {"abcd": ["ab", "cd"], "efgh": ["e", "fg", "h"]}
        return mapping[text]

    counts, detail = score_corpus(gold, perfect)
    assert counts.precision == 1.0
    assert counts.recall == 1.0
    assert counts.f1 == 1.0
    assert len(detail) == 2


def test_score_corpus_wrong_segmenter_reports_errors():
    gold = [["ab", "cd"]]

    def flat(text):
        return [text]  # never splits anything

    counts, _ = score_corpus(gold, flat)
    assert counts.tp == 0
    assert counts.fn == 1
    assert counts.precision == 0.0


def test_score_corpus_stratified_perfect_segmenter():
    gold = [["ab", "cd", "ef", "gh"]]  # "cd" is OOV; boundaries at 2,4,6
    lexicon = {"ab", "ef", "gh"}  # "cd" deliberately excluded

    def perfect(text):
        return ["ab", "cd", "ef", "gh"]

    strat = score_corpus_stratified(gold, perfect, lambda w: w in lexicon)
    # position 6 (ef|gh) is the only fully-IV junction
    assert strat.iv.tp == 1
    assert strat.iv.fp == 0
    assert strat.iv.fn == 0
    # positions 2 (ab|cd) and 4 (cd|ef) both touch the OOV word "cd"
    assert strat.oov.tp == 2
    assert strat.oov.fp == 0
    assert strat.oov.fn == 0


def test_score_corpus_stratified_missed_oov_boundary():
    gold = [["ab", "cd", "ef", "gh"]]
    lexicon = {"ab", "ef", "gh"}

    def misses_first_split(text):
        return ["abcd", "ef", "gh"]  # fails to split ab|cd (an OOV-touching boundary)

    strat = score_corpus_stratified(gold, misses_first_split, lambda w: w in lexicon)
    assert strat.iv.tp == 1  # ef|gh still found
    assert strat.oov.tp == 1  # cd|ef still found
    assert strat.oov.fn == 1  # ab|cd missed
    assert strat.oov.recall == pytest.approx(0.5)
    assert strat.oov.precision == 1.0  # no spurious OOV-stratum boundaries


def test_score_corpus_stratified_no_oov_words_gives_empty_oov_stratum():
    gold = [["ab", "cd"]]
    lexicon = {"ab", "cd"}  # everything in-lexicon

    def perfect(text):
        return ["ab", "cd"]

    strat = score_corpus_stratified(gold, perfect, lambda w: w in lexicon)
    assert strat.oov.tp == 0 and strat.oov.fp == 0 and strat.oov.fn == 0
    assert strat.oov.precision == 0.0  # empty stratum, not misleadingly 1.0
    assert strat.iv.tp == 1


def test_parse_line_nopipe():
    line = "က/n ခ/v ။/punc"
    s = _parse_line_nopipe(line)
    assert s.words == ["က", "ခ", "။"]
    assert s.tags == ["n", "v", "punc"]


def test_parse_line_pipe_merges_compound_runs():
    # mirrors the real myPOS example: အလုပ်/n|အားလပ်ရက်/n become ONE gold
    # word with no internal boundary, tag-independent
    line = "အ/n အက/n|အခ/v ။/punc"
    s = _parse_line_pipe(line)
    assert s.words == ["အ", "အကအခ", "။"]
    # the merged compound keeps the FIRST sub-unit's tag as a nominal tag
    assert s.tags[1] == "n"


def test_parse_line_pipe_without_any_pipe_matches_nopipe():
    line = "က/n ခ/v"
    assert _parse_line_pipe(line).words == _parse_line_nopipe(line).words


def test_find_disagreements_flags_bmwe_merge_gold_disagrees_with():
    gold = [["ကခ", "ဂ"]]  # gold treats first two chars as ONE word

    def plain(text):
        return list(text)  # every character its own token

    def with_bmwe(text):
        return [text[:2], text[2:]]  # BMWE merges first two chars -- matches gold here, no disagreement expected for THIS case

    disagreements = find_disagreements(gold, plain, with_bmwe)
    assert disagreements == []  # BMWE's merge matches gold -- not a disagreement


def test_find_disagreements_flags_real_mismatch():
    gold = [["က", "ခဂ"]]  # gold boundary after 1 char

    def plain(text):
        return list(text)

    def with_bmwe(text):
        return [text[:2], text[2:]]  # BMWE merges first TWO chars -- gold disagrees (boundary at 1, not 2)

    disagreements = find_disagreements(gold, plain, with_bmwe)
    assert len(disagreements) >= 1
    assert disagreements[0].direction == "bmwe_merged_gold_split"


def test_parse_alt_line_extracts_leaves_in_order():
    # a minimal ALT-style tree: two nested NOUN phrases each wrapping one
    # leaf, mirroring the real corpus's "(noun (noun X) (noun Y))" pattern
    line = "SNT.1.1\t(ROOT (NOUN (noun က) (noun ခ)) (punct ။))"
    s = _parse_alt_line(line)
    assert s.words == ["က", "ခ", "။"]
    assert s.tags == ["noun", "noun", "punct"]


def test_parse_alt_line_same_tag_at_leaf_and_phrase_level():
    # the real corpus reuses lowercase tags at BOTH leaf and phrase level
    # ("noun" wraps other "noun"s) -- leaf-ness must be structural (a
    # node whose only child is a bare word), not tag-name-based.
    line = "SNT.1.1\t(ROOT (noun (noun ကခ) (noun ဂ)))"
    s = _parse_alt_line(line)
    assert s.words == ["ကခ", "ဂ"]
    assert s.tags == ["noun", "noun"]


def test_parse_alt_line_reconstructs_original_text():
    line = (
        "SNT.1.1\t(ROOT (NOUN (noun အီတလီ) "
        "(adp သည်)) (punct ။))"
    )
    s = _parse_alt_line(line)
    assert "".join(s.words) == "အီတလီသည်။"


def test_parse_alt_line_no_tab_returns_none():
    assert _parse_alt_line("no tab in this line") is None


def test_find_disagreements_flags_punctuation_crossing_spans():
    # a gold "compound" that spans a full stop is not a lexical compound
    # at all -- almost certainly a corpus artifact, not something BMWE
    # should ever be expected to produce.
    gold = [["က", "။ခ"]]  # gold's 2nd "word" is punctuation+char fused -- pathological

    def plain(text):
        return list(text)

    def with_bmwe(text):
        return list(text)  # never merges -- forces a bmwe_split_gold_merged case

    disagreements = find_disagreements(gold, plain, with_bmwe)
    assert any(d.crosses_punctuation for d in disagreements)


def _make_disagreement(text, span_start, span_end, crosses_punctuation=False):
    return Disagreement(
        text=text,
        span_text=text,
        direction="bmwe_split_gold_merged",
        context_start=span_start,
        context_end=span_end,
        sentence_index=0,
        crosses_punctuation=crosses_punctuation,
        span_start=span_start,
        span_end=span_end,
    )


def test_categorize_punctuation_crossing_is_date_number():
    d = _make_disagreement("xx", 0, 2, crosses_punctuation=True)
    assert categorize(d) == "date_number"


def test_categorize_digit_span_is_date_number():
    d = _make_disagreement("၁၂၃", 0, 3)  # ၁၂၃ (Myanmar digits)
    assert categorize(d) == "date_number"


def test_categorize_derivation_suffix():
    # a made-up stem + the "-mhu" nominalizer suffix (မှု)
    text = "ကခ" + "မှု"
    d = _make_disagreement(text, 0, len(text))
    assert categorize(d) == "productive_derivation"


def test_categorize_proper_noun_via_callback():
    d = _make_disagreement("xx", 0, 2)
    assert categorize(d, is_proper_noun=lambda span: True) == "proper_noun"
    assert categorize(d, is_proper_noun=lambda span: False) == "genuine_compound"


def test_categorize_fallback_is_genuine_compound():
    d = _make_disagreement("xx", 0, 2)
    assert categorize(d) == "genuine_compound"


def test_sample_diverse_caps_one_per_sentence():
    many_from_one_sentence = [_make_disagreement("x", 0, 1) for _ in range(50)]
    one_from_another = _make_disagreement("y", 0, 1)
    one_from_another.sentence_index = 1
    sample = sample_diverse(many_from_one_sentence + [one_from_another], n=20)
    sentence_indices = [d.sentence_index for d in sample]
    assert len(sentence_indices) == len(set(sentence_indices))  # no duplicates
    assert len(sample) <= 20


def test_sample_diverse_empty_input():
    assert sample_diverse([], n=20) == []


def test_diff_spans_no_disagreement():
    assert diff_spans("abcd", ["ab", "cd"], ["ab", "cd"], "a", "b") == []


def test_diff_spans_reports_disagreement():
    lines = diff_spans("abcd", ["ab", "cd"], ["a", "bcd"], "ours", "theirs")
    assert lines  # non-empty when segmentations differ
    assert any("ours" in line for line in lines)
    assert any("theirs" in line for line in lines)


def test_load_external_segmentation(tmp_path):
    p = tmp_path / "seg.txt"
    p.write_text("ab cd\ne fg\n", encoding="utf-8")
    result = load_external_segmentation(str(p))
    assert result == [["ab", "cd"], ["e", "fg"]]


@pytest.mark.bench
@pytest.mark.skipif(
    os.environ.get("BURMESENLP_BENCH_TEST") != "1",
    reason="Set BURMESENLP_BENCH_TEST=1 to download myPOS and run a real evaluation",
)
def test_load_mypos_and_score_real_corpus():
    from burmesenlp.bench import load_mypos, score_corpus
    from burmesenlp.pipeline import BurmeseNLP

    sentences = load_mypos(scheme="nopipe", limit=50)
    assert len(sentences) == 50
    assert all(isinstance(s, GoldSentence) for s in sentences)

    nlp = BurmeseNLP(gazetteer=False)
    counts, detail = score_corpus([s.words for s in sentences], nlp.word_segment)
    assert 0.0 <= counts.precision <= 1.0
    assert 0.0 <= counts.recall <= 1.0
    assert len(detail) <= 50


@pytest.mark.bench
@pytest.mark.skipif(
    os.environ.get("BURMESENLP_BENCH_TEST") != "1",
    reason="Set BURMESENLP_BENCH_TEST=1 to download ALT and run a real evaluation",
)
def test_load_alt_and_score_real_corpus():
    from burmesenlp.bench import load_alt, score_corpus
    from burmesenlp.pipeline import BurmeseNLP

    sentences = load_alt(limit=50)
    assert len(sentences) == 50
    assert all(isinstance(s, GoldSentence) for s in sentences)
    assert all(s.words for s in sentences)

    nlp = BurmeseNLP(gazetteer=False)
    counts, detail = score_corpus([s.words for s in sentences], nlp.word_segment)
    assert 0.0 <= counts.precision <= 1.0
    assert 0.0 <= counts.recall <= 1.0
    assert len(detail) <= 50
