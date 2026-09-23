"""Tests for burmesenlp.spellcheck: unit tests against constructed typos
of real bundled-lexicon words, plus the canonical-mark-order guarantee."""

from __future__ import annotations

import pytest

from burmesenlp.spellcheck import correct_words, is_known, suggest

# Real bundled-lexicon words (see src/burmesenlp/lexicon/__init__.py seeds).
_SCHOOL = "ကျောင်း"  # school (noun)
_BOOK = "စာအုပ်"  # book (noun)


def test_is_known_true_for_real_lexicon_word():
    assert is_known(_SCHOOL) is True
    assert is_known(_BOOK) is True


def test_is_known_false_for_single_deletion_typo():
    typo = _SCHOOL[:-1]
    assert typo != _SCHOOL
    assert is_known(typo) is False


def test_is_known_recognizes_mark_order_variant_of_bundled_word():
    # "kyun-daw" (I/me, a bundled pronoun): medial-ya/medial-wa key order
    # swapped -- same collision pair used in test_normalize.py's
    # canonical_order() tests. Both orders must resolve to known, since
    # neither is a typo -- they're the same word, differently keyed.
    a = "ကျွန်တော်"
    b = "ကွျန်တော်"
    assert a != b
    assert is_known(a) is True
    assert is_known(b) is True


def test_suggest_returns_empty_for_already_known_word():
    assert suggest(_SCHOOL) == []


def test_suggest_finds_original_word_after_single_deletion():
    typo = _SCHOOL[:-1]
    assert _SCHOOL in suggest(typo)


def test_suggest_respects_max_suggestions():
    typo = _SCHOOL[:-1]
    assert len(suggest(typo, max_suggestions=1)) <= 1
    assert len(suggest(typo, max_suggestions=2)) <= 2


def test_suggest_rejects_non_positive_max_suggestions():
    with pytest.raises(ValueError):
        suggest(_SCHOOL, max_suggestions=0)


def test_suggest_returns_no_candidates_for_unrelated_latin_text():
    # Not Myanmar script at all -- canonicalization is a no-op and no
    # in-budget (edit distance <= 2) Myanmar lexicon word should match.
    assert suggest("xyz123") == []


def test_correct_words_leaves_known_words_unchanged():
    assert correct_words([_SCHOOL, _BOOK]) == [_SCHOOL, _BOOK]


def test_correct_words_fixes_a_known_typo_shape():
    typo = _BOOK[:-1]
    corrected = correct_words([typo])
    assert corrected[0] != typo
    assert is_known(corrected[0])


def test_correct_words_leaves_unfixable_word_unchanged():
    unfixable = "xyz123"
    assert correct_words([unfixable]) == [unfixable]


def test_is_known_type_validation():
    with pytest.raises(TypeError):
        is_known(123)  # type: ignore[arg-type]


def test_suggest_type_validation():
    with pytest.raises(TypeError):
        suggest(None)  # type: ignore[arg-type]


def test_correct_words_type_validation():
    with pytest.raises(TypeError):
        correct_words("not-a-list")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        correct_words([_SCHOOL, 123])  # type: ignore[list-item]
