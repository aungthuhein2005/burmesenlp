import pytest

from burmesenlp import BurmeseNLP
from burmesenlp.normalize import normalize


@pytest.fixture(scope="module")
def nlp():
    return BurmeseNLP()


def test_split_on_full_stop(nlp):
    text = "စာပေကိုဖတ်သည်။သူကစားသည်။"
    assert nlp.sentence_segment(text) == ["စာပေကိုဖတ်သည်။", "သူကစားသည်။"]


def test_split_on_final_particle_without_punctuation(nlp):
    text = "စာပေကိုဖတ်သည်သူကစားသည်"
    assert nlp.sentence_segment(text) == ["စာပေကိုဖတ်သည်", "သူကစားသည်"]


def test_quotative_suppresses_split(nlp):
    # ...မည်ဟုပြောသည် -- ဟု (quotative) continues the clause after မည်.
    text = "လာမည်ဟုပြောသည်"
    assert nlp.sentence_segment(text) == ["လာမည်ဟုပြောသည်"]


def test_conjunction_does_not_force_split_mid_clause(nlp):
    # နှင့် joins two nouns; the prototype wrongly split here.
    text = "ခွေးနှင့်ကြောင်ကိုမြင်သည်"
    assert nlp.sentence_segment(text) == ["ခွေးနှင့်ကြောင်ကိုမြင်သည်"]


def test_subordinate_clause_marker_does_not_split(nlp):
    # ရင် ("if/when") marks a subordinate clause inside one sentence;
    # conjunctions and clause markers never force a sentence boundary.
    text = "ကျွန်တော်အလုပ်ပြီးရင်အိမ်ပြန်မယ်"
    assert nlp.sentence_segment(text) == [text]


def test_possessive_does_not_split(nlp):
    # ၏ used as a possessive must not end a sentence.
    text = "ကျောင်း၏ဆရာကိုမြင်သည်"
    assert nlp.sentence_segment(text) == ["ကျောင်း၏ဆရာကိုမြင်သည်"]


def test_positions_are_consistent_after_normalization(nlp):
    # Zero-width space is removed by normalization; positions must refer
    # to the normalized text, verbatim.
    text = "စာ\u200bပေကိုဖတ်သည်။သူကစားသည်။"
    norm = normalize(text)
    spans = nlp.sentence_segment_with_positions(text)
    assert len(spans) == 2
    for sent, start, end in spans:
        assert norm[start:end] == sent


def test_split_disabled(nlp):
    quiet = BurmeseNLP(split_on_final_particles=False)
    text = "စာပေကိုဖတ်သည်သူကစားသည်"
    assert quiet.sentence_segment(text) == [text]


def test_empty_input(nlp):
    assert nlp.sentence_segment("") == []
