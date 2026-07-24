"""BMWE data models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

# Default POS when an MWE category has no explicit ``pos`` override.
CATEGORY_DEFAULT_POS: dict[str, str] = {
    "IDIOM": "IDIOM",
    "ORGANIZATION": "NOUN",
    "LOCATION": "NOUN",
    "PERSON": "NOUN",
    "MWE": "IDIOM",
}


def default_pos_for_category(category: str) -> str:
    return CATEGORY_DEFAULT_POS.get(category, "IDIOM")


@dataclass(frozen=True)
class MWEEntry:
    """A multi-word expression loaded into the trie."""

    text: str
    tokens: Tuple[str, ...]
    category: str
    priority: int = 0
    pos: Optional[str] = None  # optional lexical POS; else category default


@dataclass(frozen=True)
class MWEToken:
    """A merged MWE span over a pre-MWE word token sequence."""

    text: str
    tokens: Tuple[str, ...]
    category: str
    start: int
    end: int
    priority: int = 0
    pos: Optional[str] = None  # resolved POS for the merged token
    index: Optional[int] = None  # index in the post-MWE word list

    def resolved_pos(self) -> str:
        if self.pos:
            return self.pos
        return default_pos_for_category(self.category)
