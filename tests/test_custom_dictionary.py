"""Tests against the checked-in dictionary fixture."""

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
    assert nlp.lexicon.tags("ကွန်ပျူတာ") == ("NOUN",)
    assert nlp.lexicon.tags("ပရိုဂရမ်") == ("NOUN",)
    assert nlp.lexicon.tags("စစ်ဆေး") == ("VERB",)


def test_num_and_symbol_tags_are_accepted(nlp):
    assert "NUM" in nlp.lexicon.tags("ရှစ်")
    assert nlp.lexicon.tags("%") == ("SB",)


def test_seed_lexicon_survives_merge(nlp):
    assert "ရှိ" in nlp.lexicon
    assert "ကို" in nlp.lexicon
    assert "ကျွန်တော်" in nlp.lexicon


def test_overlapping_word_unions_tags(nlp):
    # Custom NUM merges with seed NUM for ရှစ်.
    assert "NUM" in nlp.lexicon.tags("ရှစ်")


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
    assert tagged["ကွန်ပျူတာ"] == "NOUN"
    assert tagged["ကို"] == "POSTP"
    assert tagged["စစ်ဆေး"] == "VERB"
    assert tagged["သည်"] == "SFP"
