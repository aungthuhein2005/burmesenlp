"""Grammar-aware sentence segmentation tests."""

import pytest

from burmesenlp import BurmeseNLP, process
from burmesenlp.normalize import normalize


@pytest.fixture(scope="module")
def nlp():
    return BurmeseNLP(gazetteer=False)


def _stripped(sents):
    return [s.strip() for s in sents]


# ---------------------------------------------------------------------------
# Acceptance tests (user-specified)
# ---------------------------------------------------------------------------


def test_greeting_then_full_clause_not_split_after_subject_marker(nlp):
    text = "မင်္ဂလာပါ။ ကျွန်တော်တို့သည် မြန်မာဘာသာစကားကို လေ့လာနေကြသည်။"
    sents = _stripped(nlp.sentence_segment(text))
    assert sents == [
        "မင်္ဂလာပါ။",
        "ကျွန်တော်တို့သည် မြန်မာဘာသာစကားကို လေ့လာနေကြသည်။",
    ]
    doc = nlp.process(text)
    assert "".join(doc.sentences) == doc.raw_text
    # Subject-marker သည် must not be SFP
    tags = dict(doc.pos_tags)
    # First သည် in the second sentence is POSTP
    is_forms = [(w, t) for w, t in doc.pos_tags if w == "သည်"]
    assert ("သည်", "POSTP") in is_forms
    assert ("သည်", "SFP") in is_forms


def test_subject_marker_does_not_end_sentence(nlp):
    text = "သူသည် ကျောင်းကို သွားသည်။"
    sents = _stripped(nlp.sentence_segment(text))
    assert sents == ["သူသည် ကျောင်းကို သွားသည်။"]
    doc = nlp.process(text)
    assert len(doc.sentences) == 1
    assert doc.pos_tags[1] == ("သည်", "POSTP")
    assert doc.pos_tags[-2] == ("သည်", "SFP")


def test_two_sentences_with_တယ်(nlp):
    text = "သူက စာဖတ်တယ်။ သူအိပ်တယ်။"
    sents = _stripped(nlp.sentence_segment(text))
    assert len(sents) == 2
    assert sents[0].endswith("တယ်။") or "စာဖတ်တယ်" in sents[0]
    assert "အိပ်တယ်" in sents[1]


def test_single_sentence_with_place_and_time(nlp):
    text = "ကျွန်တော် မန္တလေးကို မနေ့က သွားခဲ့တယ်။"
    assert len(_stripped(nlp.sentence_segment(text))) == 1


def test_idiom_sentence_stays_one(nlp):
    text = "ဒီကောင် အိတ်ပေါက်နှင့် ဖားကောက် နေတာပါကွာ။"
    assert len(_stripped(nlp.sentence_segment(text))) == 1


# ---------------------------------------------------------------------------
# Legacy / regression
# ---------------------------------------------------------------------------


def test_split_on_full_stop(nlp):
    text = "စာပေကိုဖတ်သည်။သူကစားသည်။"
    assert _stripped(nlp.sentence_segment(text)) == [
        "စာပေကိုဖတ်သည်။",
        "သူကစားသည်။",
    ]


def test_soft_split_after_vp_without_punctuation(nlp):
    # Completed VP then a new NP onset → soft split (no bare သည် rule).
    text = "စာပေကိုဖတ်သည်သူကစားသည်"
    sents = _stripped(nlp.sentence_segment(text))
    assert len(sents) == 2
    assert sents[0].endswith("သည်")
    assert "ကစား" in sents[1] or sents[1].endswith("သည်")


def test_quotative_suppresses_soft_split(nlp):
    text = "လာမည်ဟုပြောသည်"
    assert _stripped(nlp.sentence_segment(text)) == [text]


def test_conjunction_does_not_force_split_mid_clause(nlp):
    text = "ခွေးနှင့်ကြောင်ကိုမြင်သည်"
    assert _stripped(nlp.sentence_segment(text)) == [text]


def test_subordinate_clause_marker_does_not_split(nlp):
    text = "ကျွန်တော်အလုပ်ပြီးရင်အိမ်ပြန်မယ်"
    assert _stripped(nlp.sentence_segment(text)) == [text]


def test_possessive_does_not_split(nlp):
    text = "ကျောင်း၏ဆရာကိုမြင်သည်"
    assert _stripped(nlp.sentence_segment(text)) == [text]


def test_positions_are_consistent_after_normalization(nlp):
    text = "စာ\u200bပေကိုဖတ်သည်။သူကစားသည်။"
    norm = normalize(text)
    spans = nlp.sentence_segment_with_positions(text)
    assert len(spans) == 2
    for sent, start, end in spans:
        assert norm[start:end] == sent
    assert "".join(s for s, _, _ in spans) == norm


def test_soft_split_disabled(nlp):
    quiet = BurmeseNLP(split_on_final_particles=False)
    text = "စာပေကိုဖတ်သည်သူကစားသည်"
    # Punctuation-only mode: no soft VP→NP split.
    assert len(_stripped(quiet.sentence_segment(text))) == 1


def test_empty_input(nlp):
    assert nlp.sentence_segment("") == []


def test_process_sentence_word_tags_partition(nlp):
    doc = process("မင်္ဂလာပါ။ ကျွန်တော်တို့သည် မြန်မာဘာသာစကားကို လေ့လာနေကြသည်။", gazetteer=False)
    flat = [p for sent in doc.sentence_word_tags for p in sent]
    assert flat == doc.pos_tags
    assert len(doc.sentences) == 2


def test_politeness_particle_does_not_orphan_fragment(nlp):
    """ပါတယ်/ပါဘူး must stay with the predicate through ။ (not a fake NP onset)."""
    for text in (
        "ကျွန်တော်သွားခဲ့ပါတယ်။",
        "မလုပ်ပါဘူး။",
        "ရှိပါတယ်။",
    ):
        sents = _stripped(nlp.sentence_segment(text))
        assert len(sents) == 1, (text, sents)
        assert sents[0].endswith("။")


def test_soft_split_still_works_after_finite_sfp(nlp):
    text = "စာဖတ်တယ်သူအိပ်တယ်"
    sents = _stripped(nlp.sentence_segment(text))
    assert len(sents) == 2
    assert "ဖတ်" in sents[0] and sents[0].endswith("တယ်")
    assert "အိပ်" in sents[1]


def test_contrast_connector_keeps_one_sentence(nlp):
    text = "သူသွားပြီပေမဲ့သူမလာဘူး။"
    assert len(_stripped(nlp.sentence_segment(text))) == 1
