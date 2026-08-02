"""JSON / JSONL helpers for corpus sentence records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Union

from .schema import (
    ChunkRecord,
    ClauseRecord,
    EntityRecord,
    MWERecord,
    SentenceRecord,
    TokenRecord,
)

PathLike = Union[str, Path]


def sentence_to_dict(sentence: SentenceRecord) -> Dict[str, Any]:
    return sentence.to_dict()


def dumps_sentence(sentence: SentenceRecord, *, ensure_ascii: bool = False) -> str:
    return json.dumps(sentence.to_dict(), ensure_ascii=ensure_ascii)


def dumps_document(sentences: Sequence[SentenceRecord], *, ensure_ascii: bool = False) -> str:
    payload = {"sentences": [s.to_dict() for s in sentences]}
    return json.dumps(payload, ensure_ascii=ensure_ascii, indent=2)


def document_to_dict(sentences: Sequence[SentenceRecord]) -> Dict[str, Any]:
    return {"sentences": [s.to_dict() for s in sentences]}


def dumps_jsonl(
    sentences: Sequence[SentenceRecord],
    *,
    ensure_ascii: bool = False,
) -> str:
    if not sentences:
        return ""
    lines = [json.dumps(s.to_dict(), ensure_ascii=ensure_ascii) for s in sentences]
    return "\n".join(lines) + "\n"


def dump_jsonl(
    sentences: Iterable[SentenceRecord],
    path: PathLike,
    *,
    ensure_ascii: bool = False,
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for sentence in sentences:
            fh.write(json.dumps(sentence.to_dict(), ensure_ascii=ensure_ascii))
            fh.write("\n")


def load_jsonl(source: Union[str, Path]) -> List[SentenceRecord]:
    """Load sentence records from a ``.jsonl`` path or a JSONL string."""
    if isinstance(source, Path) or (isinstance(source, str) and _looks_like_path(source)):
        text = Path(source).read_text(encoding="utf-8")
    else:
        text = str(source)

    records: List[SentenceRecord] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        records.append(sentence_from_dict(json.loads(line)))
    return records


def load_json(data: Union[str, Dict[str, Any], Path]) -> List[SentenceRecord]:
    """Load from a document dict, JSON string, or file path."""
    if isinstance(data, Path) or (isinstance(data, str) and _looks_like_path(data)):
        payload = json.loads(Path(data).read_text(encoding="utf-8"))
    elif isinstance(data, str):
        payload = json.loads(data)
    else:
        payload = data

    if isinstance(payload, dict) and "sentences" in payload:
        return [sentence_from_dict(s) for s in payload["sentences"]]
    if isinstance(payload, dict) and "tokens" in payload:
        return [sentence_from_dict(payload)]
    if isinstance(payload, list):
        return [sentence_from_dict(s) for s in payload]
    raise ValueError("JSON payload must be a sentence, a sentences wrapper, or a list")


def sentence_from_dict(data: Dict[str, Any]) -> SentenceRecord:
    tokens = [
        TokenRecord(
            id=int(t["id"]),
            text=str(t["text"]),
            pos=str(t["pos"]),
            lemma=t.get("lemma"),
            norm=t.get("norm"),
            syllables=t.get("syllables"),
            features=t.get("features"),
            head=t.get("head"),
            deprel=t.get("deprel"),
        )
        for t in data.get("tokens", [])
    ]
    chunks = [
        ChunkRecord(
            id=int(c["id"]),
            type=str(c["type"]),
            start=int(c["start"]),
            end=int(c["end"]),
            function=c.get("function"),
            semantic_role=c.get("semantic_role"),
        )
        for c in data.get("chunks", [])
    ]
    clauses = [
        ClauseRecord(
            id=int(c["id"]),
            type=str(c["type"]),
            start=int(c["start"]),
            end=int(c["end"]),
            relation=c.get("relation"),
            marker=c.get("marker"),
        )
        for c in data.get("clauses", [])
    ]
    entities = [
        EntityRecord(
            id=int(e["id"]),
            label=str(e["label"]),
            start=int(e["start"]),
            end=int(e["end"]),
        )
        for e in data.get("entities", [])
    ]
    mwes = [
        MWERecord(
            id=int(m["id"]),
            type=str(m["type"]),
            start=int(m["start"]),
            end=int(m["end"]),
        )
        for m in data.get("mwe", [])
    ]
    return SentenceRecord(
        id=int(data["id"]),
        text=str(data.get("text", "")),
        tokens=tokens,
        chunks=chunks,
        clauses=clauses,
        entities=entities,
        mwe=mwes,
    )


def _looks_like_path(value: str) -> bool:
    if "\n" in value or value.lstrip().startswith(("{", "[")):
        return False
    return value.endswith((".json", ".jsonl")) or "/" in value or "\\" in value
