import json

import pytest

from burmesenlp import BurmeseNLP, Lexicon, LexiconError, cli


@pytest.fixture(scope="module")
def nlp():
    # Skip full gazetteer load in routine pipeline tests (slow).
    return BurmeseNLP(gazetteer=False)


def test_process_outputs_are_mutually_consistent(nlp):
    text = "စာပေကိုဖတ်သည်။သူကစားသည်။"
    result = nlp.process(text)

    assert set(result) == {
        "raw_text", "syllables", "words", "sentences",
        "pos_tags", "sentence_word_tags", "chunks", "mwe",
        "sentence_trees", "entities", "clauses",
    }
    assert result["entities"] == []
    # Per-sentence tags must partition the global tag list exactly.
    flattened = [pair for sent in result["sentence_word_tags"] for pair in sent]
    assert flattened == result["pos_tags"]
    assert len(result["pos_tags"]) == len(result["words"])
    # Sentence texts concatenate back to the normalized input.
    assert "".join(result["sentences"]) == result["raw_text"]


def test_process_entities_from_gazetteer(tmp_path):
    """Gazetteer NER is wired after POS into doc.entities (not chunks)."""
    (tmp_path / "male_names.json").write_text(
        json.dumps(["မင်းအောင်လှိုင်"], ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "female_names.json").write_text(
        json.dumps(["အောင်ဆန်းစုကြည်"], ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "towns.json").write_text(
        json.dumps(["ရန်ကုန်"], ensure_ascii=False),
        encoding="utf-8",
    )
    from burmesenlp import EntityType, GazetteerManager
    from burmesenlp.lexicon import Lexicon

    gaz = GazetteerManager(
        lexicon=Lexicon.default(), autoload=True, root=tmp_path
    )
    nlp = BurmeseNLP(gazetteer_manager=gaz)
    doc = nlp.process(
        "ဒေါ်အောင်ဆန်းစုကြည် ရန်ကုန်ကို သွားသည်။ ဦးမင်းအောင်လှိုင် လာသည်။"
    )
    assert doc.entities
    types = {e.entity_type for e in doc.entities}
    assert EntityType.PERSON in types
    assert EntityType.TOWN in types
    # Entities stay listed separately from chunks, but PERSON/TOWN spans
    # are also locked as NP in chunks (features.entity).
    assert all(getattr(c, "type", None) for c in doc.chunks)
    persons = [e for e in doc.entities if e.entity_type == EntityType.PERSON]
    assert any(e.attributes.get("gender") == "female" for e in persons)
    assert any(e.attributes.get("gender") == "male" for e in persons)
    # Honorific absorbed when segmented as a separate token
    if any(w == "ဒေါ်" for w in doc.words):
        assert any(e.text.startswith("ဒေါ်") for e in persons)
    # Entity-backed NP: name is one NP, not split into မင်း + လှိုင်အစိုးရရဲ့
    entity_nps = [
        c for c in doc.chunks
        if c.type.value == "NP" and c.features.get("entity") == "PERSON"
    ]
    assert entity_nps
    assert any("မင်း" in c.text and "လှိုင်" in c.text for c in entity_nps) or any(
        "အောင်ဆန်းစုကြည်" in c.text for c in entity_nps
    )
    bad_pp = [c for c in doc.chunks if c.type.value == "PP" and "လှိုင်အစိုးရ" in c.text]
    assert not bad_pp, f"name leaked into PP: {bad_pp}"
    payload = doc.to_dict()
    assert "entities" in payload
    assert payload["entities"][0]["type"] in {"PERSON", "TOWN"}


def test_chunker_locks_entity_span_as_np():
    """Unit: PhraseChunker marks entity spans before POS patterns."""
    from burmesenlp import ChunkType
    from burmesenlp.chunking.chunker import PhraseChunker
    from burmesenlp.gazetteer.models import GazetteerHit
    from burmesenlp.gazetteer.types import EntityType

    words = ["မင်း", "အောင်", "လှိုင်", "အစိုးရ", "ရဲ့"]
    tags = ["PRON", "VERB", "NOUN", "NOUN", "POSTP"]
    ent = GazetteerHit(
        text="မင်းအောင်လှိုင်",
        tokens=("မင်း", "အောင်", "လှိုင်"),
        entity_type=EntityType.PERSON,
        start=0,
        end=2,
        attributes={"gender": "male"},
    )
    chunks = PhraseChunker().chunk(words, tags, entities=[ent])
    person_np = next(c for c in chunks if c.features.get("entity") == "PERSON")
    assert person_np.type == ChunkType.NOUN_PHRASE
    assert person_np.tokens == ["မင်း", "အောင်", "လှိုင်"]
    assert person_np.pos_tags == ["PROPN", "PROPN", "PROPN"]
    assert person_np.features.get("gender") == "male"
    # Remaining အစိုးရရဲ့ should form PP, not absorb လှိုင်
    pps = [c for c in chunks if c.type == ChunkType.POSTPOSITIONAL_PHRASE]
    assert pps
    assert pps[0].tokens == ["အစိုးရ", "ရဲ့"]


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
    assert out == BurmeseNLP(gazetteer=False).word_segment(text)


def test_cli_missing_dictionary(capsys, tmp_path):
    rc = cli.main(["--dictionary", str(tmp_path / "nope.json"), "စာ"])
    assert rc == 2
    assert "error:" in capsys.readouterr().err
