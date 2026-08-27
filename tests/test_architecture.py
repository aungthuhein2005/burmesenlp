"""Architecture tests for engine dispatch and top-level process()."""

import pytest

from burmesenlp import BurmeseNLP, pos_tag, process, word_tokenize
from burmesenlp.tag import available_tag_engines
from burmesenlp.tokenize import available_word_engines, sentence_tokenize, syllable_tokenize


def test_process_matches_burmesenlp_instance():
    text = "စာပေကိုဖတ်သည်။"
    assert process(text, gazetteer=False) == BurmeseNLP(gazetteer=False).process(text)


def test_word_tokenize_longest_matches_pipeline():
    text = "မြန်မာစာပေ"
    nlp = BurmeseNLP(gazetteer=False)
    assert word_tokenize(text) == nlp.word_segment(text)
    assert word_tokenize(text, engine="longest") == nlp.word_segment(text)


def test_unknown_word_engine_raises():
    with pytest.raises(ValueError, match="unknown word tokenize engine"):
        word_tokenize("စာ", engine="sentencepiece")


def test_pos_tag_rule_engine():
    words = ["မြန်မာ", "စာပေ", "ကို"]
    nlp = BurmeseNLP(gazetteer=False)
    assert pos_tag(words) == nlp.pos_tag(words)
    assert pos_tag(words, engine="rule") == nlp.pos_tag(words)


def test_unknown_tag_engine_raises():
    with pytest.raises(ValueError, match="unknown POS tag engine"):
        pos_tag(["စာ"], engine="crf")


def test_engine_lists():
    assert available_word_engines() == ["longest"]
    assert available_tag_engines() == ["rule", "xlmr"]


def test_syllable_and_sentence_helpers():
    assert syllable_tokenize("မြန်မာ") == ["မြန်", "မာ"]
    assert sentence_tokenize("စာပေကိုဖတ်သည်။သူကစားသည်။")
