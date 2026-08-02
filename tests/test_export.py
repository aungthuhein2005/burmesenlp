"""Tests for burmesenlp.export corpus layer."""

from __future__ import annotations

import json

import pytest

from burmesenlp import BurmeseNLP, CorpusExporter, CorpusImporter, EntityType, GazetteerManager, Lexicon
from burmesenlp.export.schema import ChunkRecord, SentenceRecord


@pytest.fixture(scope="module")
def nlp():
    return BurmeseNLP(gazetteer=False)


@pytest.fixture(scope="module")
def exporter():
    return CorpusExporter()


def _assert_span_integrity(sentence: SentenceRecord) -> None:
    n = len(sentence.tokens)
    for span in (*sentence.chunks, *sentence.clauses, *sentence.entities, *sentence.mwe):
        assert 0 <= span.start <= span.end < n, (sentence.id, span, n)
    for chunk in sentence.chunks:
        assert "tokens" not in chunk.to_dict()
        assert "pos_tags" not in chunk.to_dict()
    for clause in sentence.clauses:
        payload = clause.to_dict()
        assert "phrases" not in payload
        assert "tokens" not in payload


def test_minimal_sentence_tokens_and_pos(nlp, exporter):
    doc = nlp.process("ကျွန်တော်ကျောင်းသို့သွားသည်။")
    records = exporter.to_records(doc)
    assert records
    sent = records[0]
    assert sent.tokens
    assert all(t.pos for t in sent.tokens)
    assert [t.id for t in sent.tokens] == list(range(len(sent.tokens)))
    # Sentence-local tokens partition the document words for this sentence
    tree = doc.sentence_trees[0]
    assert [t.text for t in sent.tokens] == doc.words[tree.word_start : tree.word_end]
    _assert_span_integrity(sent)


def test_export_with_chunks(nlp, exporter):
    doc = nlp.process("ကျွန်တော်ကျောင်းသို့သွားသည်။")
    sent = exporter.to_records(doc)[0]
    assert sent.chunks
    assert all(isinstance(c, ChunkRecord) for c in sent.chunks)
    for chunk in sent.chunks:
        assert chunk.type
        payload = chunk.to_dict()
        assert set(payload) <= {"id", "type", "start", "end", "function", "semantic_role"}
        assert "tokens" not in payload
    _assert_span_integrity(sent)


def test_export_with_clauses(nlp, exporter):
    doc = nlp.process("မိုးရွာလျှင်အိမ်မှာနေမည်။")
    records = exporter.to_records(doc)
    assert records
    clauses = [c for s in records for c in s.clauses]
    assert clauses
    assert any(c.type for c in clauses)
    for sent in records:
        _assert_span_integrity(sent)


def test_export_with_mwe(nlp, exporter):
    doc = nlp.process("ဒီကောင် အိတ်ပေါက်နှင့် ဖားကောက် နေတာပါကွာ")
    assert doc.mwe
    records = exporter.to_records(doc)
    mwes = [m for s in records for m in s.mwe]
    assert mwes
    assert any(m.type == "IDIOM" for m in mwes)
    for m in mwes:
        assert m.start == m.end  # post-merge single-token span
    for sent in records:
        _assert_span_integrity(sent)


def test_export_with_entities(tmp_path, exporter):
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
    gaz = GazetteerManager(lexicon=Lexicon.default(), autoload=True, root=tmp_path)
    nlp = BurmeseNLP(gazetteer_manager=gaz)
    doc = nlp.process("ဒေါ်အောင်ဆန်းစုကြည် ရန်ကုန်ကို သွားသည်။")
    assert doc.entities
    records = exporter.to_records(doc)
    entities = [e for s in records for e in s.entities]
    assert entities
    labels = {e.label for e in entities}
    assert EntityType.PERSON.value in labels or EntityType.TOWN.value in labels
    for sent in records:
        _assert_span_integrity(sent)


def test_to_json_shape_and_serialization(nlp, exporter):
    doc = nlp.process("စာပေကိုဖတ်သည်။သူကစားသည်။")
    payload = exporter.to_json(doc)
    assert "sentences" in payload
    assert isinstance(payload["sentences"], list)
    assert len(payload["sentences"]) == len(exporter.to_records(doc))
    # Stable wrapper even for multi-sentence docs
    raw = json.dumps(payload, ensure_ascii=False)
    loaded = json.loads(raw)
    assert loaded["sentences"][0]["tokens"]
    # No nested token copies inside chunks
    for sent in loaded["sentences"]:
        for chunk in sent["chunks"]:
            assert "tokens" not in chunk
            assert "pos_tags" not in chunk


def test_to_jsonl_line_count(nlp, exporter):
    doc = nlp.process("စာပေကိုဖတ်သည်။သူကစားသည်။")
    records = exporter.to_records(doc)
    text = exporter.to_jsonl(doc)
    lines = [ln for ln in text.splitlines() if ln.strip()]
    assert len(lines) == len(records)
    for line in lines:
        obj = json.loads(line)
        assert "tokens" in obj
        assert "id" in obj


def test_export_jsonl_file_and_roundtrip(nlp, exporter, tmp_path):
    docs = [
        nlp.process("ကျွန်တော်ကျောင်းသို့သွားသည်။"),
        nlp.process("သူကစားသည်။"),
    ]
    path = tmp_path / "dataset.jsonl"
    exporter.export_jsonl(docs, path)
    loaded = CorpusImporter.from_jsonl(path)
    assert loaded
    assert [s.id for s in loaded] == list(range(len(loaded)))
    # Round-trip via JSON wrapper
    payload = exporter.to_json(docs[0])
    back = CorpusImporter.from_json(payload)
    assert len(back) == len(payload["sentences"])
    assert back[0].tokens[0].text == payload["sentences"][0]["tokens"][0]["text"]


def test_conll_generation(nlp, exporter):
    doc = nlp.process("ကျွန်တော်သည်စာဖတ်သည်။")
    records = exporter.to_records(doc)
    conll = exporter.to_conll(doc)
    assert conll
    token_rows = [ln for ln in conll.splitlines() if ln.strip()]
    expected = sum(len(s.tokens) for s in records)
    assert len(token_rows) == expected
    for row in token_rows:
        cols = row.split("\t")
        assert len(cols) == 5
        assert cols[2] == "_"  # lemma placeholder
        assert cols[4] == "_"  # XPOS placeholder
        assert cols[3]  # UPOS present


def test_brat_and_labelstudio(nlp, exporter, tmp_path):
    doc = nlp.process("ကျွန်တော်ကျောင်းသို့သွားသည်။")
    brat = exporter.to_brat(doc)
    assert "txt" in brat and "ann" in brat
    assert brat["txt"]
    exporter.export_brat(doc, tmp_path, basename="sample")
    assert (tmp_path / "sample.txt").exists()
    assert (tmp_path / "sample.ann").exists()

    tasks = exporter.to_labelstudio(doc)
    assert tasks
    assert "data" in tasks[0] and "text" in tasks[0]["data"]
    assert "predictions" in tasks[0]


def test_importer_conll_stub():
    with pytest.raises(NotImplementedError):
        CorpusImporter.from_conll("1\tfoo\t_\tNOUN\t_\n")


def test_pipeline_unchanged(nlp):
    """Export must not alter Document public shape."""
    doc = nlp.process("ကျွန်တော်ကျောင်းသို့သွားသည်။")
    assert "words" in doc
    assert "chunks" in doc
    assert hasattr(doc, "to_dict")
    before = doc.to_dict()
    CorpusExporter().to_json(doc)
    assert doc.to_dict() == before
