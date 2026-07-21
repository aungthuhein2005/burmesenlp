"""Word tokenization helpers (engine-dispatched)."""

from __future__ import annotations

from typing import List, Optional

from ..lexicon import Lexicon
from .engine import run_word_engine
from .longest import WordSegmenter
from .syllable import Token


def word_tokenize(
    text: str,
    engine: str = "longest",
    *,
    lexicon: Optional[Lexicon] = None,
) -> List[str]:
    """Segment *text* into words.

    Today only ``engine=\"longest\"`` is implemented.  Future values such as
    ``\"sentencepiece\"`` or ``\"evopiece\"`` will plug into the same API.
    """
    return [t.text for t in run_word_engine(text, engine=engine, lexicon=lexicon)]


def word_tokens(
    text: str,
    engine: str = "longest",
    *,
    lexicon: Optional[Lexicon] = None,
) -> List[Token]:
    """Like :func:`word_tokenize` but returns :class:`Token` objects."""
    return run_word_engine(text, engine=engine, lexicon=lexicon)


__all__ = ["WordSegmenter", "word_tokenize", "word_tokens"]
