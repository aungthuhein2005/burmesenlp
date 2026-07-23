"""Word-segmentation tests.

Algorithm edge cases use a small controlled lexicon so expectations stay
stable as the bundled default dictionary grows.  Integration checks use
the real default lexicon.
"""

import pytest

from burmesenlp import BurmeseNLP, Lexicon


@pytest.fixture(scope="module")
def nlp():
    return BurmeseNLP()


@pytest.fixture(scope="module")
def small_nlp():
    """Minimal lexicon for deterministic longest-match / syllable-align tests."""
    lex = Lexicon(
        {
            "မြန်မာ": ["NOUN"],
            "စာပေ": ["NOUN"],
            "စာ": ["NOUN"],
            "ပေ": ["NOUN"],
            "ကို": ["POSTP"],
            "စီစဉ်": ["VERB"],
            "ခြင်း": ["NOUN"],
            "ပြီ": ["SFP"],
            "ဖတ်": ["VERB"],
            "သူမ": ["PRON"],
            "ကျောင်း": ["NOUN"],
            "ကျောင်းသား": ["NOUN"],
            "များ": ["PART"],
            "သို့": ["POSTP"],
            "သွား": ["VERB"],
            "သည်": ["SFP"],
            "သို့သော်": ["CONJ"],
            "သူ": ["PRON"],
        }
    )
    return BurmeseNLP(lexicon=lex)


def test_default_lexicon_is_large(nlp):
    assert len(nlp.lexicon) > 10_000
    assert nlp.word_segment("ကွန်ပျူတာ") == ["ကွန်ပျူတာ"]


def test_dictionary_longest_match(small_nlp):
    assert small_nlp.word_segment("မြန်မာစာပေကိုစီစဉ်ခြင်း") == [
        "မြန်မာ", "စာပေ", "ကို", "စီစဉ်", "ခြင်း",
    ]


def test_pronoun_before_noun(small_nlp):
    assert small_nlp.word_segment("သူမကျောင်းသို့သွားသည်") == [
        "သူမ", "ကျောင်း", "သို့", "သွား", "သည်",
    ]


def test_suffixes_stay_separate_words(small_nlp):
    # ALT/myPOS convention: plural/nominalizer particles are separate tokens.
    assert small_nlp.word_segment("ကျောင်းသားများ") == ["ကျောင်းသား", "များ"]


def test_numeral_plus_classifier_merges(nlp):
    assert nlp.word_segment("သုံးခု") == ["သုံးခု"]
    assert nlp.word_segment("၁၂၃ခု") == ["၁၂၃ခု"]
    assert nlp.word_segment("၅ယောက်") == ["၅ယောက်"]


def test_no_merge_across_whitespace(small_nlp):
    assert small_nlp.word_segment("မြန်မာ စာပေ") == ["မြန်မာ", "စာပေ"]
    # စာ + ပေ separated by space must NOT combine into စာပေ.
    assert small_nlp.word_segment("စာ ပေ") == ["စာ", "ပေ"]


def test_dictionary_prefix_cannot_split_a_syllable(small_nlp):
    # ပြီ is a dictionary word and a prefix of the syllable ပြီး (which is
    # not in this controlled lexicon).  Matching is syllable-aligned, so the
    # tone mark း must never be stranded as its own token.
    assert "ပြီ" in small_nlp.lexicon
    assert "ပြီး" not in small_nlp.lexicon
    assert small_nlp.word_segment("ပြီး") == ["ပြီး"]
    assert small_nlp.word_segment("စာဖတ်ပြီးပြီ") == ["စာ", "ဖတ်", "ပြီး", "ပြီ"]


def test_multiword_conjunction(small_nlp):
    assert "သို့သော်" in small_nlp.word_segment("သည်သို့သော်သူ")


def test_punctuation_and_foreign_text(nlp):
    assert nlp.word_segment("Hello မြန်မာ!") == ["Hello", "မြန်မာ", "!"]


def test_word_tokens_have_valid_offsets(nlp):
    from burmesenlp.normalize import normalize

    text = "မြန်မာ စာပေကိုဖတ်သည်။"
    norm = normalize(text)
    for tok in nlp.word_tokens(text):
        assert norm[tok.start : tok.end] == tok.text


def test_empty_input(nlp):
    assert nlp.word_segment("") == []
