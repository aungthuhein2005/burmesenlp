"""Verb-phrase grammar loader (YAML-backed)."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .models import ChunkRule, ChunkType
from .rules import grammar_dir, load_phrase_rules


def load_verb_rules(directory: Optional[Path] = None) -> List[ChunkRule]:
    d = directory or grammar_dir()
    return [r for r in load_phrase_rules(d / "phrase_rules.yml") if r.type == ChunkType.VERB_PHRASE]
