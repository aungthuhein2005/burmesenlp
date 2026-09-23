"""Tests for burmesenlp.transliterate.romanize (BGN/PCGN).

Every case here traces to a *verified* source, not a guess: the BGN/PCGN
1970 Agreement's own worked examples (Notes 2-4 and 5), or a well-known
place-name romanization independently confirmed against real usage. See
src/burmesenlp/transliterate/bgn_pcgn.py's module docstring for sources
and for what this v1 deliberately does not attempt.
"""

from __future__ import annotations

import pytest

from burmesenlp.normalize import canonical_order
from burmesenlp.transliterate import romanize

# -- BGN/PCGN 1970 Agreement's own worked examples (Notes 2-4) ---------

def test_note2_bare_consonant_examples():
    assert romanize("မဒမ") == "madama"
    assert romanize("အက") == "aga"  # also exercises voicing: k -> g after a vowel
    assert romanize("ကလိ") == "kali"


def test_note3_word_initial_vowel_carrier_examples():
    assert romanize("သာငယ်") == "thangè"
    assert romanize("အိုဘဲ့") == "obè"
    assert romanize("အပ်") == "at"


def test_note5_stacked_consonant_example():
    assert romanize("သဒ္ဓ") == "thadda"


# -- Independently-verified place names ---------------------------------

def test_yangon():
    assert romanize("ရန်ကုန်") == "yangôn"


def test_pyin_oo_lwin():
    assert romanize("ပြင်ဦးလွင်") == "pyinulwin"


# -- Kinzi (not in the source document; this module's own inference, see
# the module docstring) cross-validated against well-known spellings ---

def test_kinzi_mingala():
    assert romanize("မင်္ဂလာ") == "mingala"


def test_kinzi_singapore():
    assert romanize("စင်္ကာပူ") == "singabu"


# -- Structural properties ----------------------------------------------

def test_non_myanmar_text_passes_through_unchanged():
    assert romanize("hello 123!") == "hello 123!"
    assert romanize("") == ""


def test_digits_are_romanized():
    assert romanize("၂၀၂၃") == "2023"


def test_type_validation():
    with pytest.raises(TypeError):
        romanize(123)  # type: ignore[arg-type]


def test_documented_contraction_passes_through_unromanized():
    # ကျွန်ုပ် ("I") is one of normalize's documented Contractions
    # sequences -- no verified romanization was found, so this module
    # leaves it as-is rather than guessing (see the module docstring).
    word = "ကျွန်ုပ်"
    assert romanize(word) == word


def test_never_raises_on_bundled_lexicon():
    # Every real word in the bundled lexicon should at least produce
    # *some* output without raising, whether or not every syllable in
    # it is confidently romanized (unhandled syllables fall back to the
    # original Myanmar text -- see romanize()'s docstring).
    from burmesenlp.lexicon import Lexicon

    for word in list(Lexicon.default().words())[:2000]:
        result = romanize(word)
        assert isinstance(result, str)
        assert result  # never empty for a non-empty input


def test_mark_order_variant_romanizes_identically():
    # canonical_order()'s own collision-pair fixture (kyun-daw "I/me"):
    # medial ya/wa key order swapped, same intended word. romanize()
    # should not care which order the marks were typed in.
    a = "ကျွန်တော်"
    b = "ကွျန်တော်"
    assert a != b
    assert canonical_order(a) == canonical_order(b)
    assert romanize(a) == romanize(b)
