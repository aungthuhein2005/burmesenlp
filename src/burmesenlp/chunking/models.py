"""Chunking data models and errors."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Mapping, Optional, Sequence, Tuple


class ChunkType(Enum):
    NOUN_PHRASE = "NP"
    VERB_PHRASE = "VP"
    POSTPOSITIONAL_PHRASE = "PP"
    ADJECTIVE_PHRASE = "ADJP"
    NUMERAL_PHRASE = "NUMP"
    CLAUSE = "CLAUSE"
    GREETING = "GREETING"
    FIXED_EXPRESSION = "FIXED_EXPRESSION"
    FIXED_VERB = "FIXED_VERB"


@dataclass(frozen=True)
class Chunk:
    """A shallow phrase span over already-tagged tokens.

    ``start`` / ``end`` are inclusive token indices into the input sequence.
    """

    type: ChunkType
    text: str
    tokens: List[str]
    pos_tags: List[str]
    start: int
    end: int
    features: Mapping[str, str] = field(default_factory=dict)


class GrammarError(ValueError):
    """Invalid grammar YAML or pattern DSL."""


@dataclass(frozen=True)
class ChunkRule:
    """One compiled pattern entry (one row under ``phrases[].patterns``)."""

    id: str
    name: str
    type: ChunkType
    priority: int
    pattern: str
    source: str = ""
    features: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class PhraseMarkers:
    """Boundary markers from ``phrase_markers.yml``."""

    noun_phrase_end: Mapping[str, Tuple[str, ...]]
    verb_phrase_end: Mapping[str, Tuple[str, ...]]
    clause_boundary: Mapping[str, Tuple[str, ...]]

    def all_clause_markers(self) -> Tuple[str, ...]:
        out: List[str] = []
        for vals in self.clause_boundary.values():
            out.extend(vals)
        return tuple(dict.fromkeys(out))


@dataclass(frozen=True)
class PhraseExceptions:
    """Special cases from ``phrase_exceptions.yml``."""

    fixed_expressions: Tuple[Tuple[str, ChunkType], ...]
    never_split: Tuple[str, ...]
    special_phrases: Tuple[Tuple[str, ChunkType], ...]


def normalize_pos_input(pos_tags: Sequence[object]) -> List[str]:
    """Accept ``List[str]`` or ``List[Tuple[str, str]]`` and return tag strings."""
    out: List[str] = []
    for item in pos_tags:
        if isinstance(item, tuple) and len(item) == 2:
            out.append(str(item[1]))
        else:
            out.append(str(item))
    return out


def make_chunk(
    chunk_type: ChunkType,
    words: Sequence[str],
    tags: Sequence[str],
    start: int,
    end: int,
    features: Optional[Mapping[str, str]] = None,
) -> Chunk:
    tokens = list(words[start : end + 1])
    pos = list(tags[start : end + 1])
    return Chunk(
        type=chunk_type,
        text="".join(tokens),
        tokens=tokens,
        pos_tags=pos,
        start=start,
        end=end,
        features=dict(features or {}),
    )
