import json

import pytest

from burmesenlp import BurmeseNLP, Lexicon, LexiconError, cli


@pytest.fixture(scope="module")
def nlp():
    return BurmeseNLP()


def test_process_outputs_are_mutually_consistent(nlp):
    text = "စာပေကိုဖတ်သည်။သူကစားသည်။"
    result = nlp.process(text)

    assert set(result) == {
        "raw_text", "syllables", "words", "sentences",
        "pos_tags", "sentence_word_tags", "chunks",
    }
    # Per-sentence tags must partition the global tag list exactly.
    flattened = [pair for sent in result["sentence_word_tags"] for pair in sent]
    assert flattened == result["pos_tags"]
    assert len(result["pos_tags"]) == len(result["words"])
    # Sentence texts concatenate back to the normalized input.
    assert "".join(result["sentences"]) == result["raw_text"]


def test_document_to_dict_is_json_serializable(nlp):
    doc = nlp.process("စာဖတ်သည်။")
    payload = doc.to_dict()
    raw = json.dumps(payload, ensure_ascii=False)
    assert "chunks" in payload
    assert all(isinstance(c["type"], str) for c in payload["chunks"])
    assert json.loads(raw)["words"] == doc.words


def test_missing_dictionary_raises(tmp_path):
    with pytest.raises(LexiconError):
        BurmeseNLP(dictionary_path=str(tmp_path / "nope.json"))


def test_custom_lexicon_and_dictionary_roundtrip(tmp_path, nlp):
    nlp2 = BurmeseNLP(lexicon=Lexicon.default())
    nlp2.add_to_dictionary("နည်းပညာ", ["NOUN"])
    assert nlp2.word_segment("နည်းပညာ") == ["နည်းပညာ"]

    path = tmp_path / "dict.json"
    nlp2.save_dictionary(str(path))
    nlp3 = BurmeseNLP(dictionary_path=str(path))
    assert nlp3.word_segment("နည်းပညာ") == ["နည်းပညာ"]


def test_dictionary_path_merges_onto_seed(tmp_path):
    path = tmp_path / "domain.json"
    path.write_text(
        json.dumps({"နည်းပညာ": ["NOUN"]}, ensure_ascii=False),
        encoding="utf-8",
    )
    nlp = BurmeseNLP(dictionary_path=str(path))
    assert nlp.word_segment("နည်းပညာ") == ["နည်းပညာ"]
    # Seed entries are still present after loading a tiny overlay.
    assert "ရှိ" in nlp.lexicon
    assert nlp.word_segment("ရှိသည်") == ["ရှိ", "သည်"]


def test_dictionary_txt_import_via_pipeline(tmp_path):
    path = tmp_path / "domain.txt"
    path.write_text("နည်းပညာ\tNOUN\n", encoding="utf-8")
    nlp = BurmeseNLP(dictionary_path=str(path))
    assert nlp.word_segment("နည်းပညာ") == ["နည်းပညာ"]
    assert "ကို" in nlp.lexicon


def test_get_stats(nlp):
    stats = nlp.get_stats("စာပေကိုဖတ်သည်။")
    assert stats["sentence_count"] == 1
    assert stats["word_count"] >= 4
    assert stats["syllable_count"] >= stats["word_count"] - 1
    assert isinstance(stats["pos_distribution"], dict)


def test_crf_features(nlp):
    feats = nlp.extract_features_for_crf("မြန်မာ")
    assert len(feats) == 2
    assert feats[0]["BOS"] is True
    assert feats[-1]["EOS"] is True
    assert feats[0]["has_asat"] is True  # မြန် contains ်


def test_cli_json_words(capsys):
    text = "မြန်မာစာပေ"
    rc = cli.main(["--json", "--mode", "words", text])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out == BurmeseNLP().word_segment(text)


def test_cli_missing_dictionary(capsys, tmp_path):
    rc = cli.main(["--dictionary", str(tmp_path / "nope.json"), "စာ"])
    assert rc == 2
    assert "error:" in capsys.readouterr().err
