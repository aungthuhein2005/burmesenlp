"""Canonical non-redundant corpus export records.

Spans use inclusive, sentence-local token indices. Optional linguistic
fields are omitted from ``to_dict()`` when unset so exporters never invent
data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional


def _omit_none(data: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in data.items() if v is not None}


@dataclass(frozen=True)
class TokenRecord:
    """One token in a sentence."""

    id: int
    text: str
    pos: str
    lemma: Optional[str] = None
    norm: Optional[str] = None
    syllables: Optional[List[str]] = None
    features: Optional[Mapping[str, str]] = None
    head: Optional[int] = None
    deprel: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return _omit_none(
            {
                "id": self.id,
                "text": self.text,
                "pos": self.pos,
                "lemma": self.lemma,
                "norm": self.norm,
                "syllables": list(self.syllables) if self.syllables is not None else None,
                "features": dict(self.features) if self.features is not None else None,
                "head": self.head,
                "deprel": self.deprel,
            }
        )


@dataclass(frozen=True)
class ChunkRecord:
    """Phrase chunk as a token span (no nested tokens)."""

    id: int
    type: str
    start: int
    end: int
    function: Optional[str] = None
    semantic_role: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return _omit_none(
            {
                "id": self.id,
                "type": self.type,
                "start": self.start,
                "end": self.end,
                "function": self.function,
                "semantic_role": self.semantic_role,
            }
        )


@dataclass(frozen=True)
class ClauseRecord:
    """Clause as a token span (no nested chunks/tokens)."""

    id: int
    type: str
    start: int
    end: int
    relation: Optional[str] = None
    marker: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = _omit_none(
            {
                "id": self.id,
                "type": self.type,
                "start": self.start,
                "end": self.end,
                "relation": self.relation,
                "marker": self.marker if self.marker else None,
            }
        )
        return data


@dataclass(frozen=True)
class EntityRecord:
    """Named entity as a token span."""

    id: int
    label: str
    start: int
    end: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "start": self.start,
            "end": self.end,
        }


@dataclass(frozen=True)
class MWERecord:
    """Multi-word expression as a token span."""

    id: int
    type: str
    start: int
    end: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "start": self.start,
            "end": self.end,
        }


@dataclass(frozen=True)
class SentenceRecord:
    """One training-friendly sentence with span-based annotations."""

    id: int
    text: str
    tokens: List[TokenRecord] = field(default_factory=list)
    chunks: List[ChunkRecord] = field(default_factory=list)
    clauses: List[ClauseRecord] = field(default_factory=list)
    entities: List[EntityRecord] = field(default_factory=list)
    mwe: List[MWERecord] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "tokens": [t.to_dict() for t in self.tokens],
            "chunks": [c.to_dict() for c in self.chunks],
            "clauses": [c.to_dict() for c in self.clauses],
            "entities": [e.to_dict() for e in self.entities],
            "mwe": [m.to_dict() for m in self.mwe],
        }
