"""Gazetteer hit payloads."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .types import EntityType


@dataclass(frozen=True)
class GazetteerHit:
    """A matched gazetteer surface form over a token sequence."""

    text: str
    tokens: Tuple[str, ...]
    entity_type: EntityType
    start: int = 0
    end: int = 0  # inclusive token index when from find_all / longest_match
    attributes: Dict[str, Any] = field(default_factory=dict)

    @property
    def type(self) -> str:
        return self.entity_type.value
