"""Label Studio task JSON export."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

from .offsets import sentence_surface, span_char_offsets, token_char_spans
from .schema import SentenceRecord


def to_labelstudio_tasks(sentences: Sequence[SentenceRecord]) -> List[Dict[str, Any]]:
    """One Label Studio task per sentence with span predictions."""
    tasks: List[Dict[str, Any]] = []
    for sentence in sentences:
        surface = sentence_surface(sentence)
        token_spans = token_char_spans(surface, sentence.tokens)
        results: List[Dict[str, Any]] = []

        for entity in sentence.entities:
            _add_result(results, surface, token_spans, entity.start, entity.end, entity.label)
        for chunk in sentence.chunks:
            _add_result(
                results,
                surface,
                token_spans,
                chunk.start,
                chunk.end,
                f"CHUNK/{chunk.type}",
            )
        for mwe in sentence.mwe:
            _add_result(
                results,
                surface,
                token_spans,
                mwe.start,
                mwe.end,
                f"MWE/{mwe.type}",
            )
        for clause in sentence.clauses:
            _add_result(
                results,
                surface,
                token_spans,
                clause.start,
                clause.end,
                f"CLAUSE/{clause.type}",
            )

        tasks.append(
            {
                "data": {"text": surface},
                "predictions": [{"result": results}],
            }
        )
    return tasks


def _add_result(
    results: List[Dict[str, Any]],
    surface: str,
    token_spans: Sequence,
    start: int,
    end: int,
    label: str,
) -> None:
    char_start, char_end = span_char_offsets(token_spans, start, end)
    if char_end <= char_start:
        return
    results.append(
        {
            "from_name": "label",
            "to_name": "text",
            "type": "labels",
            "value": {
                "start": char_start,
                "end": char_end,
                "text": surface[char_start:char_end],
                "labels": [label],
            },
        }
    )
