import pytest

from burmesenlp import BurmeseNLP


@pytest.fixture(scope="module")
def nlp():
    return BurmeseNLP()


def test_dictionary_longest_match(nlp):
    assert nlp.word_segment("မြန်မာစာပေကိုစီစဉ်ခြင်း") == [
        "မြန်မာ", "စာပေ", "ကို", "စီစဉ်", "ခြင်း",
    ]


def test_pronoun_before_noun(nlp):
    assert nlp.word_segment("သူမကျောင်းသို့သွားသည်") == [
        "သူမ", "ကျောင်း", "သို့", "သွား", "သည်",
    ]


def test_suffixes_stay_separate_words(nlp):
    # ALT/myPOS convention: plural/nominalizer particles are separate tokens.
    assert nlp.word_segment("ကျောင်းသားများ") == ["ကျောင်းသား", "များ"]


def test_numeral_plus_classifier_merges(nlp):
    assert nlp.word_segment("သုံးခု") == ["သုံးခု"]
    assert nlp.word_segment("၁၂၃ခု") == ["၁၂၃ခု"]
    assert nlp.word_segment("၅ယောက်") == ["၅ယောက်"]


def test_no_merge_across_whitespace(nlp):
    assert nlp.word_segment("မြန်မာ စာပေ") == ["မြန်မာ", "စာပေ"]
    # စာ + ပေ separated by space must NOT combine into စာပေ.
    assert nlp.word_segment("စာ ပေ") == ["စာ", "ပေ"]


def test_dictionary_prefix_cannot_split_a_syllable(nlp):
    # ပြီ is a dictionary word and a prefix of the syllable ပြီး (which is
    # not in the dictionary).  Matching is syllable-aligned, so the tone
    # mark း must never be stranded as its own token.
    assert "ပြီ" in nlp.lexicon
    assert "ပြီး" not in nlp.lexicon
    assert nlp.word_segment("ပြီး") == ["ပြီး"]
    assert nlp.word_segment("စာဖတ်ပြီးပြီ") == ["စာ", "ဖတ်", "ပြီး", "ပြီ"]


def test_multiword_conjunction(nlp):
    assert "သို့သော်" in nlp.word_segment("သည်သို့သော်သူ")


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
