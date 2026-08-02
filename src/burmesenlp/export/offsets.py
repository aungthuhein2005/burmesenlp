"""Character-offset helpers shared by BRAT and Label Studio exporters."""

from __future__ import annotations

from typing import List, Sequence, Tuple

from .schema import SentenceRecord, TokenRecord


def token_char_spans(text: str, tokens: Sequence[TokenRecord]) -> List[Tuple[int, int]]:
    """Compute exclusive-end character spans for tokens inside ``text``.

    Walks forward with substring search so Myanmar (usually space-free) text
    aligns without inventing separators. Unmatched tokens fall back to a
    contiguous cursor advance by token length.
    """
    spans: List[Tuple[int, int]] = []
    cursor = 0
    for token in tokens:
        form = token.text
        if not form:
            spans.append((cursor, cursor))
            continue
        idx = text.find(form, cursor)
        if idx < 0:
            # Fallback: place at cursor if it fits, else append at end.
            if cursor + len(form) <= len(text) and text[cursor : cursor + len(form)] == form:
                idx = cursor
            else:
                idx = min(cursor, len(text))
                end = min(idx + len(form), len(text))
                spans.append((idx, end))
                cursor = end
                continue
        end = idx + len(form)
        spans.append((idx, end))
        cursor = end
    return spans


def span_char_offsets(
    token_spans: Sequence[Tuple[int, int]],
    start: int,
    end: int,
) -> Tuple[int, int]:
    """Map inclusive token indices to exclusive-end character offsets."""
    if not token_spans or start > end or start < 0 or end >= len(token_spans):
        return 0, 0
    return token_spans[start][0], token_spans[end][1]


def sentence_surface(sentence: SentenceRecord) -> str:
    return sentence.text or "".join(t.text for t in sentence.tokens)
