"""Production golden / regression tests for BurmeseNLP 1.0.

These fixtures use real Burmese text and the bundled default lexicon.
Keep expectations on stable closed-class / common words; avoid brittle
compounds that longest-match may re-chunk when the lexicon grows.
"""

from __future__ import annotations

from burmesenlp import (
    POS_TAGS,
    normalize,
    pos_tag,
    process,
    sentence_tokenize,
    to_unicode,
    uni2zg,
    word_tokenize,
    zg2uni,
)

GO_TO_SCHOOL = "ကျွန်တော်ကျောင်းသို့သွားသည်။"
GO_TO_SCHOOL_WORDS = ["ကျွန်တော်", "ကျောင်း", "သို့", "သွား", "သည်", "။"]


def test_normalize_strips_zero_width_and_nfc():
    raw = "\ufeff\u1005\u102c\u200b\u1015\u1031"
    assert normalize(raw) == "\u1005\u102c\u1015\u1031"
    assert normalize("\u1025\u102e") == "\u1026"


def test_unicode_prose_word_and_sentence_tokenize():
    assert word_tokenize(GO_TO_SCHOOL) == GO_TO_SCHOOL_WORDS
    assert sentence_tokenize(GO_TO_SCHOOL) == [GO_TO_SCHOOL]


def test_unicode_prose_pos_and_process():
    tags = pos_tag(GO_TO_SCHOOL_WORDS)
    assert [w for w, _ in tags] == GO_TO_SCHOOL_WORDS
    assert all(t in POS_TAGS for _, t in tags)
    assert tags[0] == ("ကျွန်တော်", "PRON")
    assert tags[1] == ("ကျောင်း", "NOUN")
    assert tags[2] == ("သို့", "POSTP")
    assert tags[3] == ("သွား", "VERB")
    assert tags[4] == ("သည်", "SFP")
    assert tags[-1] == ("။", "PUNCT")

    doc = process(GO_TO_SCHOOL)
    assert doc["words"] == GO_TO_SCHOOL_WORDS
    assert doc["pos_tags"] == tags
    assert "".join(doc["sentences"]) == doc["raw_text"]
    assert doc["syllables"]
    flattened = [pair for sent in doc["sentence_word_tags"] for pair in sent]
    assert flattened == doc["pos_tags"]


def test_zawgyi_converted_text_matches_unicode_pipeline():
    zg = uni2zg(GO_TO_SCHOOL)
    uni = zg2uni(zg)
    assert to_unicode(zg) == uni
    assert word_tokenize(uni) == GO_TO_SCHOOL_WORDS
    assert process(uni)["words"] == GO_TO_SCHOOL_WORDS


def test_mixed_english_and_burmese():
    text = "Hello မြန်မာ NLP"
    words = word_tokenize(text)
    assert words == ["Hello", "မြန်မာ", "NLP"]
    tags = pos_tag(words)
    assert len(tags) == 3
    assert tags[1][0] == "မြန်မာ"
    assert tags[1][1] in POS_TAGS


def test_punctuation_and_multi_sentence_paragraph():
    para = "ကျွန်တော်ကျောင်းသို့သွားသည်။ သူစာအုပ်ကိုဖတ်သည်။"
    sentences = sentence_tokenize(para)
    assert len(sentences) == 2
    assert sentences[0].endswith("။")
    assert sentences[1].endswith("။")

    words = word_tokenize(para)
    assert "ကျွန်တော်" in words
    assert "စာအုပ်" in words
    assert words.count("။") == 2

    doc = process(para)
    assert len(doc["sentences"]) == 2
    assert len(doc["pos_tags"]) == len(doc["words"])
    assert all(t in POS_TAGS for _, t in doc["pos_tags"])


def test_myanmar_digits_and_classifier():
    assert word_tokenize("၁၂၃ခု") == ["၁၂၃ခု"]
    assert word_tokenize("၅ယောက်") == ["၅ယောက်"]


def test_long_paragraph_process_is_non_empty():
    paragraph = (
        "မြန်မာနိုင်ငံသည်အရှေ့တောင်အာရှတွင်တည်ရှိသည်။ "
        "ကျွန်တော်ကျောင်းသို့သွားသည်။ "
        "သူစာအုပ်ကိုဖတ်သည်။ Hello world!"
    )
    doc = process(paragraph)
    assert len(doc["words"]) >= 10
    assert len(doc["sentences"]) >= 2
    assert len(doc["syllables"]) >= len(doc["words"])
    assert all(isinstance(w, str) and w for w in doc["words"])
    assert all(tag in POS_TAGS for _, tag in doc["pos_tags"])
