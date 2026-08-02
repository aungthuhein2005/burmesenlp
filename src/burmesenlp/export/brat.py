"""BRAT ``.txt`` / ``.ann`` export."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Sequence, Tuple, Union

from .offsets import sentence_surface, span_char_offsets, token_char_spans
from .schema import SentenceRecord

PathLike = Union[str, Path]


def dumps_brat(sentences: Sequence[SentenceRecord]) -> Dict[str, str]:
    """Return ``{"txt": ..., "ann": ...}`` for a document's sentences.

    Sentences are joined with newlines. Annotation labels use namespaces:
    entities as-is, chunks as ``CHUNK/<type>``, MWEs as ``MWE/<type>``,
    clauses as ``CLAUSE/<type>``.
    """
    txt_parts: List[str] = []
    ann_lines: List[str] = []
    tid = 1
    offset = 0

    for sentence in sentences:
        surface = sentence_surface(sentence)
        txt_parts.append(surface)
        token_spans = token_char_spans(surface, sentence.tokens)

        for entity in sentence.entities:
            tid = _append_ann(
                ann_lines,
                tid,
                entity.label,
                entity.start,
                entity.end,
                token_spans,
                surface,
                offset,
            )
        for chunk in sentence.chunks:
            tid = _append_ann(
                ann_lines,
                tid,
                f"CHUNK/{chunk.type}",
                chunk.start,
                chunk.end,
                token_spans,
                surface,
                offset,
            )
        for mwe in sentence.mwe:
            tid = _append_ann(
                ann_lines,
                tid,
                f"MWE/{mwe.type}",
                mwe.start,
                mwe.end,
                token_spans,
                surface,
                offset,
            )
        for clause in sentence.clauses:
            tid = _append_ann(
                ann_lines,
                tid,
                f"CLAUSE/{clause.type}",
                clause.start,
                clause.end,
                token_spans,
                surface,
                offset,
            )

        offset += len(surface) + 1  # account for joining newline

    txt = "\n".join(txt_parts)
    ann = "\n".join(ann_lines) + ("\n" if ann_lines else "")
    return {"txt": txt, "ann": ann}


def write_brat(
    sentences: Sequence[SentenceRecord],
    out_dir: PathLike,
    *,
    basename: str = "document",
) -> Tuple[Path, Path]:
    """Write ``basename.txt`` and ``basename.ann`` under ``out_dir``."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    payload = dumps_brat(sentences)
    txt_path = out / f"{basename}.txt"
    ann_path = out / f"{basename}.ann"
    txt_path.write_text(payload["txt"], encoding="utf-8")
    ann_path.write_text(payload["ann"], encoding="utf-8")
    return txt_path, ann_path


def _append_ann(
    lines: List[str],
    tid: int,
    label: str,
    start: int,
    end: int,
    token_spans: Sequence[Tuple[int, int]],
    surface: str,
    offset: int,
) -> int:
    char_start, char_end = span_char_offsets(token_spans, start, end)
    if char_end <= char_start:
        return tid
    abs_start = offset + char_start
    abs_end = offset + char_end
    mention = surface[char_start:char_end]
    # BRAT disallows spaces/tabs/newlines in type names — keep slash ok.
    safe_label = label.replace(" ", "_")
    lines.append(f"T{tid}\t{safe_label} {abs_start} {abs_end}\t{mention}")
    return tid + 1
