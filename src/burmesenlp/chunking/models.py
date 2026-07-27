"""Chunking & clause-syntax data models.

Layers
------
* ``Chunk`` — shallow phrase span from the phrase chunker (NP / VP / PP / …).
* ``Phrase`` — phrase node used in the clause tree (may nest children).
* ``Clause`` — clause node whose children are ``Phrase`` objects.
* ``SyntaxSentence`` — sentence node whose children are ``Clause`` objects.

Relative clauses are **not** top-level ``Clause`` nodes; they nest inside NP
as ``RelativeModifier`` + ``HeadNoun`` children.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Mapping, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Phrase chunk types (shallow chunker)
# ---------------------------------------------------------------------------


class ChunkType(Enum):
    NOUN_PHRASE = "NP"
    VERB_PHRASE = "VP"
    POSTPOSITIONAL_PHRASE = "PP"
    ADJECTIVE_PHRASE = "ADJP"
    NUMERAL_PHRASE = "NUMP"
    GREETING = "GREETING"
    FIXED_EXPRESSION = "FIXED_EXPRESSION"
    FIXED_VERB = "FIXED_VERB"
    # Legacy clause overlays (kept for serialization / older callers).
    # Prefer ClauseType on Clause / SyntaxSentence — do not emit these from
    # the V1 ClauseParser into Document.chunks.
    CLAUSE = "CLAUSE"
    MAIN_CLAUSE = "MAIN_CLAUSE"
    SUBORDINATE_CLAUSE = "SUBORDINATE_CLAUSE"
    RELATIVE_CLAUSE = "RELATIVE_CLAUSE"
    CONDITIONAL_CLAUSE = "CONDITIONAL_CLAUSE"


CLAUSE_TYPES = frozenset(
    {
        ChunkType.CLAUSE,
        ChunkType.MAIN_CLAUSE,
        ChunkType.SUBORDINATE_CLAUSE,
        ChunkType.RELATIVE_CLAUSE,
        ChunkType.CONDITIONAL_CLAUSE,
    }
)


def is_clause_type(chunk_type: ChunkType) -> bool:
    return chunk_type in CLAUSE_TYPES


# ---------------------------------------------------------------------------
# Clause types (V1) — extensible Enum; add members for V2+
# ---------------------------------------------------------------------------


class ClauseType(Enum):
    MAIN = "MAIN"
    CONDITIONAL = "CONDITIONAL"
    PURPOSE = "PURPOSE"
    REASON = "REASON"
    RELATIVE = "RELATIVE"  # nested in NP only — not a Sentence-level clause
    CONTRAST = "CONTRAST"


# Top-level clause types allowed on SyntaxSentence.clauses
TOP_LEVEL_CLAUSE_TYPES = frozenset(
    {
        ClauseType.MAIN,
        ClauseType.CONDITIONAL,
        ClauseType.PURPOSE,
        ClauseType.REASON,
        ClauseType.CONTRAST,
    }
)


# ---------------------------------------------------------------------------
# Grammatical function vs semantic role (kept separate)
# ---------------------------------------------------------------------------


class GrammaticalFunction(Enum):
    SUBJECT = "SUBJECT"
    OBJECT = "OBJECT"
    ADJUNCT = "ADJUNCT"
    POSSESSOR = "POSSESSOR"
    PREDICATE = "PREDICATE"
    MODIFIER = "MODIFIER"
    HEAD = "HEAD"


class SemanticRole(Enum):
    AGENT = "AGENT"
    SUBJECT = "SUBJECT"
    OBJECT = "OBJECT"
    GOAL = "GOAL"
    EXPERIENCER = "EXPERIENCER"
    BENEFICIARY = "BENEFICIARY"
    SOURCE = "SOURCE"
    LOCATION = "LOCATION"
    INSTRUMENT = "INSTRUMENT"
    DESTINATION = "DESTINATION"
    DIRECTION = "DIRECTION"
    TIME = "TIME"
    POSSESSOR = "POSSESSOR"
    STANDARD = "STANDARD"
    COMPARISON = "COMPARISON"
    COMITATIVE = "COMITATIVE"
    COORDINATION = "COORDINATION"
    TOPIC = "TOPIC"
    MANNER = "MANNER"


# Nested NP child roles for relative constructions
ROLE_RELATIVE_MODIFIER = "RelativeModifier"
ROLE_HEAD_NOUN = "HeadNoun"


# ---------------------------------------------------------------------------
# Shallow chunk (phrase chunker output)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Syntax tree nodes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phrase:
    """Phrase node in the clause tree.

    Syntax (``type``, ``grammatical_function``) is separate from semantics
    (``semantic_role``). Relative clauses nest via ``children`` with
    ``role`` = RelativeModifier / HeadNoun.
    """

    type: ChunkType
    text: str
    tokens: List[str]
    pos_tags: List[str]
    start: int
    end: int
    grammatical_function: Optional[str] = None
    semantic_role: Optional[str] = None
    role: Optional[str] = None  # RelativeModifier | HeadNoun | PurposeVP | …
    children: Tuple["Phrase", ...] = ()
    features: Mapping[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "text": self.text,
            "tokens": list(self.tokens),
            "pos_tags": list(self.pos_tags),
            "start": self.start,
            "end": self.end,
            "grammatical_function": self.grammatical_function,
            "semantic_role": self.semantic_role,
            "role": self.role,
            "features": dict(self.features),
            "children": [c.to_dict() for c in self.children],
        }


@dataclass(frozen=True)
class Clause:
    """Clause node: type + ordered phrase children (never raw words alone).

    ``phrases`` / ``chunks`` are the same hierarchical phrase nodes — use
    either name; ``chunks`` matches the Document layer naming.
    """

    type: ClauseType
    text: str
    phrases: Tuple[Phrase, ...]
    start: int
    end: int
    relation: Optional[str] = None
    marker: str = ""
    features: Mapping[str, str] = field(default_factory=dict)

    @property
    def chunks(self) -> Tuple[Phrase, ...]:
        """Alias for ``phrases`` (Sentence → Clause → Phrase hierarchy)."""
        return self.phrases

    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "relation": self.relation,
            "marker": self.marker,
            "features": dict(self.features),
            "phrases": [p.to_dict() for p in self.phrases],
            "chunks": [p.to_dict() for p in self.phrases],
        }


@dataclass(frozen=True)
class SyntaxSentence:
    """Sentence → Clause → Phrase tree for one segmented sentence."""

    text: str
    start: int  # char offsets into normalized text
    end: int
    word_start: int
    word_end: int
    clauses: Tuple[Clause, ...]
    phrases: Tuple[Phrase, ...]  # sentence-level phrases after relative nesting

    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "word_start": self.word_start,
            "word_end": self.word_end,
            "phrases": [p.to_dict() for p in self.phrases],
            "clauses": [c.to_dict() for c in self.clauses],
        }


# ---------------------------------------------------------------------------
# Grammar resource models
# ---------------------------------------------------------------------------


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
class ClauseSettings:
    """Parser behaviour from ``clause_rules.yml`` ``settings``."""

    require_final_vp: bool = True
    allow_nested_relative: bool = True
    merge_consecutive_pp: bool = False
    prefer_longest_match: bool = True
    allow_empty_np: bool = False


@dataclass(frozen=True)
class ClauseKindRules:
    """One clause kind: markers + inherited phrase patterns + metadata."""

    name: str
    clause_type: ClauseType
    markers: Tuple[str, ...]
    phrase_patterns: Tuple[Tuple[str, ...], ...]
    end_markers: Tuple[str, ...] = ()
    relation: str = ""
    precedence: int = 0
    nesting: bool = False
    inherit: str = ""


@dataclass(frozen=True)
class ClauseRules:
    """Full clause grammar from ``clause_rules.yml``."""

    kinds: Mapping[str, ClauseKindRules]
    # Longest-first flat list of (marker, kind_name) for scanning
    markers_longest: Tuple[Tuple[str, str], ...]
    settings: ClauseSettings = field(default_factory=ClauseSettings)
    # Named pattern templates (basic_clause, relative_clause, …)
    pattern_templates: Mapping[str, Tuple[Tuple[str, ...], ...]] = field(
        default_factory=dict
    )

    def kind(self, name: str) -> Optional[ClauseKindRules]:
        return self.kinds.get(name)

    def marker_texts(self) -> Tuple[str, ...]:
        return tuple(m for m, _ in self.markers_longest)

    @property
    def sentence_end(self) -> Tuple[str, ...]:
        main = self.kinds.get("main")
        return main.end_markers if main else ()

    def kinds_by_precedence(self) -> Tuple[ClauseKindRules, ...]:
        """Non-main kinds sorted by precedence ascending (lower fires first)."""
        items = [k for n, k in self.kinds.items() if n != "main"]
        items.sort(key=lambda k: (k.precedence, k.name))
        return tuple(items)


@dataclass(frozen=True)
class PostpositionRole:
    text: str
    default_role: str
    grammatical_function: str
    possible_roles: Tuple[str, ...]


@dataclass(frozen=True)
class PostpositionRoles:
    by_text: Mapping[str, PostpositionRole]

    def get(self, text: str) -> Optional[PostpositionRole]:
        return self.by_text.get(text)


@dataclass(frozen=True)
class PhraseExceptions:
    """Special cases from ``phrase_exceptions.yml``."""

    fixed_expressions: Tuple[Tuple[str, ChunkType], ...]
    never_split: Tuple[str, ...]
    special_phrases: Tuple[Tuple[str, ChunkType], ...]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def chunk_to_phrase(
    chunk: Chunk,
    *,
    grammatical_function: Optional[str] = None,
    semantic_role: Optional[str] = None,
    role: Optional[str] = None,
    children: Tuple[Phrase, ...] = (),
    features: Optional[Mapping[str, str]] = None,
) -> Phrase:
    feats = dict(chunk.features)
    if features:
        feats.update(features)
    return Phrase(
        type=chunk.type,
        text=chunk.text,
        tokens=list(chunk.tokens),
        pos_tags=list(chunk.pos_tags),
        start=chunk.start,
        end=chunk.end,
        grammatical_function=grammatical_function,
        semantic_role=semantic_role,
        role=role,
        children=children,
        features=feats,
    )


# Map ClauseType → legacy ChunkType for optional flat overlays
_CLAUSE_TO_CHUNK = {
    ClauseType.MAIN: ChunkType.MAIN_CLAUSE,
    ClauseType.CONDITIONAL: ChunkType.CONDITIONAL_CLAUSE,
    ClauseType.REASON: ChunkType.SUBORDINATE_CLAUSE,
    ClauseType.PURPOSE: ChunkType.SUBORDINATE_CLAUSE,
    ClauseType.CONTRAST: ChunkType.SUBORDINATE_CLAUSE,
    ClauseType.RELATIVE: ChunkType.RELATIVE_CLAUSE,
}


def clause_type_to_chunk_type(clause_type: ClauseType) -> ChunkType:
    return _CLAUSE_TO_CHUNK.get(clause_type, ChunkType.CLAUSE)
