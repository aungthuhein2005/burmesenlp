import pytest

from burmesenlp.normalize import normalize
from burmesenlp.tokenize.syllable import syllable_segment, tokenize

CASES = {
    "မြန်မာ": ["မြန်", "မာ"],
    "သည်": ["သည်"],
    "လုပ်": ["လုပ်"],
    "စက်": ["စက်"],
    "ခြင်း": ["ခြင်း"],
    "ဖြ": ["ဖြ"],
    "ဖြစ်": ["ဖြစ်"],
    "စီစဉ်": ["စီ", "စဉ်"],
    "စမ်းသပ်ခြင်း": ["စမ်း", "သပ်", "ခြင်း"],
    "မြန်မာစာပေ": ["မြန်", "မာ", "စာ", "ပေ"],
    "ကို": ["ကို"],
    "ခဲ့": ["ခဲ့"],
    "ပြီ": ["ပြီ"],
    "လား": ["လား"],
    "အရမ်း": ["အ", "ရမ်း"],
    "သိပ်မဟုတ်": ["သိပ်", "မ", "ဟုတ်"],
    "အံ့": ["အံ့"],
    "ကျောင်း": ["ကျောင်း"],
    "ကျွန်တော်": ["ကျွန်", "တော်"],
}


@pytest.mark.parametrize("text,expected", CASES.items())
def test_basic_syllables(text, expected):
    assert syllable_segment(text) == expected


def test_kinzi_stays_intact():
    # The prototype emitted the stack virama as a bogus standalone syllable.
    assert syllable_segment("အင်္ဂါ") == ["အင်္ဂါ"]
    assert syllable_segment("င်္ဂါ") == ["င်္ဂါ"]


def test_stacked_consonants_follow_sylbreak_convention():
    # Stacked (Pali) clusters stay attached to the preceding syllable.
    assert syllable_segment("ဝိဇ္ဇာ") == ["ဝိဇ္ဇာ"]
    assert syllable_segment("မန္တလေး") == ["မန္တ", "လေး"]


def test_digits_group_into_one_token():
    assert syllable_segment("၁၂၃") == ["၁၂၃"]
    assert syllable_segment("က၁၂") == ["က", "၁၂"]


def test_myanmar_punctuation_is_separate():
    assert syllable_segment("စာ။") == ["စာ", "။"]
    assert syllable_segment("စာ၊ပေ") == ["စာ", "၊", "ပေ"]


def test_mixed_scripts():
    assert syllable_segment("Hello မြန်မာ!") == ["Hello", "မြန်", "မာ", "!"]


def test_zero_width_characters_do_not_split_syllables():
    assert syllable_segment("စာ\u200bပေ") == ["စာ", "ပေ"]


def test_empty_input():
    assert syllable_segment("") == []


def test_token_offsets_reconstruct_text():
    text = normalize("မြန်မာ စာပေ။ Hello!")
    for tok in tokenize(text):
        assert text[tok.start : tok.end] == tok.text


def test_defensive_on_stray_combining_marks():
    # Bare asat / virama should not crash or loop forever.
    assert syllable_segment("\u103a") == ["\u103a"]
    assert syllable_segment("\u1039") == ["\u1039"]
