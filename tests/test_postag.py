import pytest

from burmesenlp import BurmeseNLP
from burmesenlp.lexicon import Lexicon


@pytest.fixture(scope="module")
def nlp():
    return BurmeseNLP(gazetteer=False)


def test_basic_tagging(nlp):
    words = ["မြန်မာ", "စာပေ", "ကို", "စီစဉ်", "ခြင်း"]
    tags = dict(nlp.pos_tag(words))
    assert tags["မြန်မာ"] == "NOUN"
    assert tags["စာပေ"] == "NOUN"
    assert tags["ကို"] == "POSTP"
    assert tags["စီစဉ်"] == "VERB"


def test_punctuation_and_digits(nlp):
    assert nlp.pos_tag(["။"]) == [("။", "PUNCT")]
    assert nlp.pos_tag(["၊"]) == [("၊", "PUNCT")]
    assert nlp.pos_tag(["၁၂၃"]) == [("၁၂၃", "NUM")]
    assert nlp.pos_tag(["123"]) == [("123", "NUM")]
    assert nlp.pos_tag(["သုံးခု"]) == [("သုံးခု", "NUM")]


def test_foreign_words(nlp):
    assert nlp.pos_tag(["Hello"]) == [("Hello", "FW")]


def test_pron_noun_disambiguation(nlp):
    tagged = nlp.pos_tag(["သူ", "စာ", "ဖတ်", "သည်"])
    assert tagged[0] == ("သူ", "PRON")


def test_possessive_vs_final_particle(nlp):
    mid = nlp.pos_tag(["ကျောင်း", "၏", "ဆရာ"])
    assert mid[1] == ("၏", "POSTP")
    final = nlp.pos_tag(["စာ", "ဖတ်", "၏"])
    assert final[2] == ("၏", "PART")


def test_noun_verb_disambiguation_via_context(nlp):
    tagged = nlp.pos_tag(["ရွာ", "မှာ", "နေ", "သည်"])
    assert tagged[2] == ("နေ", "VERB")


def test_thwa_verb_via_finite_particle(nlp):
    assert Lexicon.default().tags("သွား") == ("VERB", "NOUN")
    tagged = nlp.pos_tag(["သွား", "သည်"])
    assert tagged == [("သွား", "VERB"), ("သည်", "SFP")]


def test_thwa_verb_via_negation(nlp):
    tagged = nlp.pos_tag(["မ", "သွား"])
    assert tagged == [("မ", "PART"), ("သွား", "VERB")]


def test_thwa_noun_via_case_marker(nlp):
    tagged = nlp.pos_tag(["သွား", "ကို"])
    assert tagged[0] == ("သွား", "NOUN")
    assert tagged[1] == ("ကို", "POSTP")


def test_po_adverb_before_verb(nlp):
    tagged = nlp.pos_tag(["ပို", "လုပ်"])
    assert tagged[0] == ("ပို", "ADV")
    assert tagged[1] == ("လုပ်", "VERB")


def test_verb_aux_finite_grammar_pattern(nlp):
    tagged = nlp.pos_tag(["ခံစား", "နေ", "တယ်"])
    assert tagged == [
        ("ခံစား", "VERB"),
        ("နေ", "AUX"),
        ("တယ်", "SFP"),
    ]


def test_go_to_school_sentence(nlp):
    tagged = nlp.pos_tag(["ကျွန်တော်", "ကျောင်း", "သို့", "သွား", "သည်", "။"])
    assert tagged[0] == ("ကျွန်တော်", "PRON")
    assert tagged[1] == ("ကျောင်း", "NOUN")
    assert tagged[2] == ("သို့", "POSTP")
    assert tagged[3] == ("သွား", "VERB")
    assert tagged[4] == ("သည်", "SFP")
    assert tagged[5] == ("။", "PUNCT")


def test_ထား_after_verb_is_aux(nlp):
    tagged = nlp.pos_tag(["အားတင်း", "ထား", "ကြ"])
    assert tagged[0][1] == "VERB"
    assert tagged[1] == ("ထား", "AUX")
    assert tagged[2] == ("ကြ", "PART")


def test_က_after_noun_is_postp(nlp):
    tagged = nlp.pos_tag(["မန္တလေး", "က"])
    assert tagged[1] == ("က", "POSTP")


def test_နှင့်_between_nouns_is_conj(nlp):
    tagged = nlp.pos_tag(["ကျောင်း", "နှင့်", "အိမ်"])
    assert tagged[1] == ("နှင့်", "CONJ")


def test_နှင့်_before_verb_is_postp(nlp):
    tagged = nlp.pos_tag(["သူ", "နှင့်", "သွား"])
    assert tagged[1] == ("နှင့်", "POSTP")


def test_unknown_defaults(nlp):
    assert nlp.pos_tag(["ဆောက်လုပ်ရေး"]) == [("ဆောက်လုပ်ရေး", "NOUN")]


def test_empty(nlp):
    assert nlp.pos_tag([]) == []


def test_akae_khat_before_plural_is_noun(nlp):
    """Occupation noun + တွေ must not stay VERB (else chunker builds a VP)."""
    tagged = nlp.pos_tag(["နိုင်ငံရေး", "အကဲခတ်", "တွေ", "ကတော့"])
    assert tagged[1] == ("အကဲခတ်", "NOUN")
    assert tagged[2][1] in ("PART", "NOUN")  # plural particle
    assert tagged[3] == ("ကတော့", "POSTP")


def test_akae_khat_as_verb_when_finite(nlp):
    tagged = nlp.pos_tag(["သူ", "အကဲခတ်", "သည်"])
    assert tagged[1] == ("အကဲခတ်", "VERB")


def test_akae_khat_တွေ_chunks_as_np(nlp):
    from burmesenlp.chunking.models import ChunkType

    doc = nlp.process("နိုင်ငံရေးအကဲခတ်တွေကတော့")
    tags = dict(doc.pos_tags)
    assert tags.get("အကဲခတ်") == "NOUN"
    assert tags.get("ကတော့") == "POSTP"
    # Topic marker attaches into a PP with the subject NP (not a lone NP).
    pp_texts = [c.text for c in doc.chunks if c.type == ChunkType.POSTPOSITIONAL_PHRASE]
    assert any("အကဲခတ်" in t and "ကတော့" in t for t in pp_texts)
    lone_kato = [
        c
        for c in doc.chunks
        if c.text == "ကတော့" and c.type == ChunkType.NOUN_PHRASE
    ]
    assert not lone_kato
    vp_texts = [c.text for c in doc.chunks if c.type == ChunkType.VERB_PHRASE]
    assert not any("အကဲခတ်" in t for t in vp_texts)
