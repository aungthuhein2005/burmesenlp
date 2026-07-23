"""Rule-based shallow phrase chunking (NP / VP / PP / CLAUSE).

Consumes word tokens and POS tags; never modifies POS tags.
Grammar patterns live under ``burmesenlp/corpus/grammar/*.yaml``.
"""

from __future__ import annotations

from .chunker import PhraseChunker, chunk, chunk_from_tokens
from .models import Chunk, ChunkType, GrammarError
from .rules import CompiledGrammar, default_grammar, reload_default_grammar

__all__ = [
    "Chunk",
    "ChunkType",
    "CompiledGrammar",
    "GrammarError",
    "PhraseChunker",
    "chunk",
    "chunk_from_tokens",
    "default_grammar",
    "reload_default_grammar",
]
