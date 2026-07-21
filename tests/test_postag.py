import pytest

from burmesenlp import BurmeseNLP


@pytest.fixture(scope="module")
def nlp():
    return BurmeseNLP()


def test_basic_tagging(nlp):
    words = ["မြန်မာ", "စာပေ", "ကို", "စီစဉ်", "ခြင်း"]
    tags = dict(nlp.pos_tag(words))
    assert tags["မြန်မာ"] == "n"
    assert tags["စာပေ"] == "n"
    assert tags["ကို"] == "ppm"
    assert tags["စီစဉ်"] == "v"


def test_punctuation_and_digits(nlp):
    assert nlp.pos_tag(["။"]) == [("။", "punc")]
    assert nlp.pos_tag(["၊"]) == [("၊", "punc")]
    assert nlp.pos_tag(["၁၂၃"]) == [("၁၂၃", "num")]
    assert nlp.pos_tag(["123"]) == [("123", "num")]
    assert nlp.pos_tag(["သုံးခု"]) == [("သုံးခု", "num")]


def test_foreign_words(nlp):
    assert nlp.pos_tag(["Hello"]) == [("Hello", "fw")]


def test_pron_noun_disambiguation(nlp):
    # Sentence-initial သူ -> pronoun.
    tagged = nlp.pos_tag(["သူ", "စာ", "ဖတ်", "သည်"])
    assert tagged[0] == ("သူ", "pron")


def test_possessive_vs_final_particle(nlp):
    # Mid-sentence ၏ -> possessive marker (ppm).
    mid = nlp.pos_tag(["ကျောင်း", "၏", "ဆရာ"])
    assert mid[1] == ("၏", "ppm")
    # Sentence-final ၏ -> particle.
    final = nlp.pos_tag(["စာ", "ဖတ်", "၏"])
    assert final[2] == ("၏", "part")


def test_noun_verb_disambiguation_via_context(nlp):
    # နေ is noun (sun) and verb (live/stay); after ppm မှာ -> verb.
    tagged = nlp.pos_tag(["ရွာ", "မှာ", "နေ", "သည်"])
    assert tagged[2] == ("နေ", "v")


def test_unknown_defaults(nlp):
    # Unknown Myanmar word with nominalizer suffix -> noun.
    assert nlp.pos_tag(["ဆောက်လုပ်ရေး"]) == [("ဆောက်လုပ်ရေး", "n")]


def test_empty(nlp):
    assert nlp.pos_tag([]) == []
