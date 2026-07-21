"""Word-tokenizer engine registry.

v1 ships only ``\"longest\"`` (dictionary greedy match).  Future engines
(SentencePiece, BPE, WordPiece, EvoPiece) register here without changing
call sites such as ``word_tokenize(..., engine=...)``.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

from ..lexicon import Lexicon
from ..normalize import normalize
from .longest import WordSegmenter
from .syllable import Token, tokenize

# engine name -> factory(lexicon) -> segmenter with .segment(tokens) -> List[Token]
WordEngineFactory = Callable[[Lexicon], WordSegmenter]

_WORD_ENGINES: Dict[str, WordEngineFactory] = {
    "longest": WordSegmenter,
}


def available_word_engines() -> List[str]:
    return sorted(_WORD_ENGINES)


def get_word_engine(name: str) -> WordEngineFactory:
    try:
        return _WORD_ENGINES[name]
    except KeyError as exc:
        raise ValueError(
            f"unknown word tokenize engine {name!r}; "
            f"available: {available_word_engines()}"
        ) from exc


def register_word_engine(name: str, factory: WordEngineFactory) -> None:
    """Register a future word tokenizer backend (v2+)."""
    _WORD_ENGINES[name] = factory


def run_word_engine(
    text: str,
    *,
    engine: str = "longest",
    lexicon: Optional[Lexicon] = None,
) -> List[Token]:
    """Normalize *text*, syllable-tokenize, then run the named word engine."""
    lex = lexicon if lexicon is not None else Lexicon.default()
    factory = get_word_engine(engine)
    segmenter = factory(lex)
    return segmenter.segment(tokenize(normalize(text)))
