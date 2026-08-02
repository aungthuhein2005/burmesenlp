"""CoNLL-style export for corpus sentence records."""

from __future__ import annotations

from typing import Sequence

from .schema import SentenceRecord


def dumps_conll(sentences: Sequence[SentenceRecord]) -> str:
    """Serialize sentences as CoNLL-U-inspired blocks (blank-line separated).

    Columns: ``ID FORM LEMMA UPOS XPOS``
    Missing optional fields become ``_``.
    """
    blocks: list[str] = []
    for sentence in sentences:
        lines: list[str] = []
        for token in sentence.tokens:
            lemma = token.lemma if token.lemma else "_"
            xpos = "_"
            # 1-based token ids for CoNLL convention
            lines.append(
                f"{token.id + 1}\t{token.text}\t{lemma}\t{token.pos}\t{xpos}"
            )
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + ("\n" if blocks else "")
