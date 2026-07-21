"""Tests against the checked-in myPOS-style dictionary fixture."""

from pathlib import Path

import pytest

from burmesenlp import BurmeseNLP

DICT_PATH = Path(__file__).with_name("custom_dictionary.json")


@pytest.fixture(scope="module")
def nlp():
    return BurmeseNLP(dictionary_path=str(DICT_PATH))


def test_custom_entries_are_loaded(nlp):
    assert "ကွန်ပျူတာ" in nlp.lexicon
    assert "အင်တာနက်" in nlp.lexicon
    assert "ပရိုဂရမ်" in nlp.lexicon
    assert nlp.lexicon.tags("ကွန်ပျူတာ") == ("n",)
    assert nlp.lexicon.tags("ပရိုဂရမ်") == ("n",)
    assert nlp.lexicon.tags("စစ်ဆေး") == ("v",)


def test_mypos_tags_tn_and_sb_are_accepted(nlp):
    # myPOS distinguishes digit numbers (num) from text numbers (tn),
    # and symbols (sb) from punctuation (punc).
    assert "tn" in nlp.lexicon.tags("ရှစ်")
    assert nlp.lexicon.tags("%") == ("sb",)


def test_seed_lexicon_survives_merge(nlp):
    # Domain overlay must not replace the built-in seed.
    assert "ရှိ" in nlp.lexicon
    assert "ကို" in nlp.lexicon
    assert "ကျွန်တော်" in nlp.lexicon


def test_overlapping_word_unions_tags(nlp):
    # Seed tags ရှစ် as num; custom adds tn — merge keeps both.
    assert set(nlp.lexicon.tags("ရှစ်")) == {"num", "tn"}
    # Preference order surfaces tn first for text numerals.
    assert nlp.lexicon.tags("ရှစ်")[0] == "tn"


def test_domain_word_segmentation(nlp):
    assert nlp.word_segment("ကွန်ပျူတာ") == ["ကွန်ပျူတာ"]
    assert nlp.word_segment("အင်တာနက်") == ["အင်တာနက်"]
    assert nlp.word_segment("ကွန်ပျူတာနှင့်အင်တာနက်") == [
        "ကွန်ပျူတာ",
        "နှင့်",
        "အင်တာနက်",
    ]


def test_domain_pos_tags(nlp):
    tagged = dict(nlp.pos_tag(nlp.word_segment("ကွန်ပျူတာကိုစစ်ဆေးသည်")))
    assert tagged["ကွန်ပျူတာ"] == "n"
    assert tagged["ကို"] == "ppm"
    assert tagged["စစ်ဆေး"] == "v"
    assert tagged["သည်"] == "part"
