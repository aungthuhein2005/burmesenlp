"""Rule-based POS tagger (engine=\"rule\").

Orchestrates:
  1. lexicon / heuristic candidate lookup
  2. priority-ordered context rule filtering
  3. multi-token grammar rule filtering
  4. preference-order fallback among remaining tags

Public API stays ``POSTagger.tag(words) -> List[Tuple[str, str]]``.
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

from ..lexicon import Lexicon
from .candidates import lookup_candidates
from .disambiguator import disambiguate


class POSTagger:
    """Filter-based rule POS tagger: candidates → rules → final tags."""

    def __init__(self, lexicon: Lexicon):
        self._lexicon = lexicon

    def tag(self, words: Sequence[str]) -> List[Tuple[str, str]]:
        words = list(words)
        if not words:
            return []
        candidates = [lookup_candidates(w, self._lexicon) for w in words]
        tags = disambiguate(words, candidates)
        return list(zip(words, tags))
