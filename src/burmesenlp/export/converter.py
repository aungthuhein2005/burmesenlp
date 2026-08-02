"""Convert pipeline ``Document`` objects into span-based ``SentenceRecord``s.

Remaps document-level inclusive token indices to sentence-local indices.
Does not invent linguistic fields that the pipeline does not provide.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from ..chunking.models import Chunk, Phrase, SyntaxSentence
from ..gazetteer.models import GazetteerHit
from ..mwe.models import MWEToken
from ..pipeline.document import Document
from .schema import (
    ChunkRecord,
    ClauseRecord,
    EntityRecord,
    MWERecord,
    SentenceRecord,
    TokenRecord,
)


def document_to_sentences(doc: Document) -> List[SentenceRecord]:
    """Convert a ``Document`` into one ``SentenceRecord`` per sentence.

    Prefer ``sentence_trees`` for boundaries. If trees are empty but
    ``words`` exist, synthesize a single sentence covering the full document
    (robustness for partial pipeline outputs).
    """
    trees = list(doc.sentence_trees)
    if trees:
        return [
            _sentence_from_tree(doc, sent, sent_id)
            for sent_id, sent in enumerate(trees)
        ]

    if not doc.words:
        return []

    # Fallback: one synthetic sentence over all words.
    return [_sentence_from_bounds(doc, 0, len(doc.words), text=_fallback_text(doc), sent_id=0)]


def _fallback_text(doc: Document) -> str:
    if doc.sentences:
        return doc.sentences[0] if len(doc.sentences) == 1 else "".join(doc.sentences)
    return doc.raw_text or "".join(doc.words)


def _sentence_from_tree(doc: Document, sent: SyntaxSentence, sent_id: int) -> SentenceRecord:
    return _sentence_from_bounds(
        doc,
        sent.word_start,
        sent.word_end,
        text=sent.text,
        sent_id=sent_id,
        tree=sent,
    )


def _sentence_from_bounds(
    doc: Document,
    ws: int,
    we: int,
    *,
    text: str,
    sent_id: int,
    tree: Optional[SyntaxSentence] = None,
) -> SentenceRecord:
    tokens = _tokens(doc, ws, we)
    n = len(tokens)

    if tree is not None and tree.phrases:
        chunks = _chunks_from_phrases(tree.phrases, ws, n)
    else:
        chunks = _chunks_from_flat(doc.chunks, ws, we, n)

    clauses = _clauses_from_tree(tree, ws, n) if tree is not None else []
    entities = _entities(doc.entities, ws, we, n)
    mwes = _mwes(doc.mwe, ws, we, n)

    return SentenceRecord(
        id=sent_id,
        text=text,
        tokens=tokens,
        chunks=chunks,
        clauses=clauses,
        entities=entities,
        mwe=mwes,
    )


def _tokens(doc: Document, ws: int, we: int) -> List[TokenRecord]:
    words = doc.words[ws:we]
    tags = doc.pos_tags[ws:we]
    out: List[TokenRecord] = []
    for i, word in enumerate(words):
        pos = tags[i][1] if i < len(tags) else "UNK"
        out.append(TokenRecord(id=i, text=word, pos=pos))
    return out


def _span_in_sentence(start: int, end: int, ws: int, we: int) -> Optional[Tuple[int, int]]:
    """Remap inclusive document indices to sentence-local; None if outside."""
    if start < ws or end > we - 1 or start > end:
        return None
    return start - ws, end - ws


def _valid_local(start: int, end: int, n: int) -> bool:
    return n > 0 and 0 <= start <= end < n


def _flatten_phrases(phrases: Sequence[Phrase]) -> List[Phrase]:
    out: List[Phrase] = []

    def walk(nodes: Sequence[Phrase]) -> None:
        for p in nodes:
            out.append(p)
            if p.children:
                walk(p.children)

    walk(phrases)
    return out


def _chunks_from_phrases(
    phrases: Sequence[Phrase],
    ws: int,
    n: int,
) -> List[ChunkRecord]:
    records: List[ChunkRecord] = []
    for phrase in _flatten_phrases(phrases):
        remapped = _span_in_sentence(phrase.start, phrase.end, ws, ws + n)
        if remapped is None:
            continue
        local_start, local_end = remapped
        if not _valid_local(local_start, local_end, n):
            continue
        records.append(
            ChunkRecord(
                id=len(records),
                type=phrase.type.value if hasattr(phrase.type, "value") else str(phrase.type),
                start=local_start,
                end=local_end,
                function=phrase.grammatical_function,
                semantic_role=phrase.semantic_role,
            )
        )
    records.sort(key=lambda c: (c.start, c.end, c.type))
    return [
        ChunkRecord(
            id=i,
            type=c.type,
            start=c.start,
            end=c.end,
            function=c.function,
            semantic_role=c.semantic_role,
        )
        for i, c in enumerate(records)
    ]


def _chunks_from_flat(
    chunks: Sequence[Chunk],
    ws: int,
    we: int,
    n: int,
) -> List[ChunkRecord]:
    records: List[ChunkRecord] = []
    for chunk in chunks:
        remapped = _span_in_sentence(chunk.start, chunk.end, ws, we)
        if remapped is None:
            continue
        local_start, local_end = remapped
        if not _valid_local(local_start, local_end, n):
            continue
        records.append(
            ChunkRecord(
                id=len(records),
                type=chunk.type.value if hasattr(chunk.type, "value") else str(chunk.type),
                start=local_start,
                end=local_end,
            )
        )
    records.sort(key=lambda c: (c.start, c.end, c.type))
    return [
        ChunkRecord(id=i, type=c.type, start=c.start, end=c.end)
        for i, c in enumerate(records)
    ]


def _clauses_from_tree(
    tree: SyntaxSentence,
    ws: int,
    n: int,
) -> List[ClauseRecord]:
    records: List[ClauseRecord] = []
    for clause in tree.clauses:
        remapped = _span_in_sentence(clause.start, clause.end, ws, ws + n)
        if remapped is None:
            continue
        local_start, local_end = remapped
        if not _valid_local(local_start, local_end, n):
            continue
        records.append(
            ClauseRecord(
                id=len(records),
                type=clause.type.value if hasattr(clause.type, "value") else str(clause.type),
                start=local_start,
                end=local_end,
                relation=clause.relation,
                marker=clause.marker or None,
            )
        )
    records.sort(key=lambda c: (c.start, c.end, c.type))
    return [
        ClauseRecord(
            id=i,
            type=c.type,
            start=c.start,
            end=c.end,
            relation=c.relation,
            marker=c.marker,
        )
        for i, c in enumerate(records)
    ]


def _entities(
    entities: Sequence[GazetteerHit],
    ws: int,
    we: int,
    n: int,
) -> List[EntityRecord]:
    records: List[EntityRecord] = []
    for hit in entities:
        remapped = _span_in_sentence(hit.start, hit.end, ws, we)
        if remapped is None:
            continue
        local_start, local_end = remapped
        if not _valid_local(local_start, local_end, n):
            continue
        records.append(
            EntityRecord(
                id=len(records),
                label=hit.entity_type.value,
                start=local_start,
                end=local_end,
            )
        )
    records.sort(key=lambda e: (e.start, e.end, e.label))
    return [
        EntityRecord(id=i, label=e.label, start=e.start, end=e.end)
        for i, e in enumerate(records)
    ]


def _mwes(
    mwes: Sequence[MWEToken],
    ws: int,
    we: int,
    n: int,
) -> List[MWERecord]:
    """Map MWEs via post-merge ``index`` only (never misuse pre-MWE spans)."""
    records: List[MWERecord] = []
    for mwe in mwes:
        if mwe.index is None:
            continue
        if not (ws <= mwe.index < we):
            continue
        local = mwe.index - ws
        if not _valid_local(local, local, n):
            continue
        records.append(
            MWERecord(
                id=len(records),
                type=mwe.category,
                start=local,
                end=local,
            )
        )
    records.sort(key=lambda m: (m.start, m.end, m.type))
    return [
        MWERecord(id=i, type=m.type, start=m.start, end=m.end)
        for i, m in enumerate(records)
    ]
