"""Clause / marker grammar loader (YAML-backed)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

from .models import PhraseMarkers
from .rules import grammar_dir, load_markers


def load_clause_markers(directory: Optional[Path] = None) -> Tuple[str, ...]:
    d = directory or grammar_dir()
    markers: PhraseMarkers = load_markers(d / "phrase_markers.yml")
    return markers.all_clause_markers()
