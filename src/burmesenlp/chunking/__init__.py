"""Rule-based shallow phrase chunking + phrase-based clause parsing.

Consumes word tokens and POS tags; never modifies POS tags.
Grammar: ``burmesenlp/corpus/grammar/phrase_*.yml``, ``clause_rules.yml``,
``semantic_roles.yml``.
"""

from __future__ import annotations

from .chunker import PhraseChunker, chunk, chunk_from_tokens
from .clause import ClauseParser, is_valid_main_clause, load_clause_markers
from .models import (
    CLAUSE_TYPES,
    TOP_LEVEL_CLAUSE_TYPES,
    Chunk,
    ChunkType,
    Clause,
    ClauseSettings,
    ClauseType,
    GrammarError,
    Phrase,
    SyntaxSentence,
    is_clause_type,
)
from .rules import (
    CompiledGrammar,
    default_grammar,
    load_clause_rules,
    load_postposition_roles,
    reload_default_grammar,
)

__all__ = [
    "CLAUSE_TYPES",
    "TOP_LEVEL_CLAUSE_TYPES",
    "Chunk",
    "ChunkType",
    "Clause",
    "ClauseParser",
    "ClauseSettings",
    "ClauseType",
    "CompiledGrammar",
    "GrammarError",
    "Phrase",
    "PhraseChunker",
    "SyntaxSentence",
    "chunk",
    "chunk_from_tokens",
    "default_grammar",
    "is_clause_type",
    "is_valid_main_clause",
    "load_clause_markers",
    "load_clause_rules",
    "load_postposition_roles",
    "reload_default_grammar",
]
