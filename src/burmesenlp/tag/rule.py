"""Rule-based POS tagger (engine=\"rule\").

Orchestrates:
  1. lexicon / heuristic candidate lookup
  2. optional BMWE overrides (merged idiom / entity POS)
  3. priority-ordered context rule filtering
  4. multi-token grammar rule filtering
  5. preference-order fallback among remaining tags

Public API stays ``POSTagger.tag(words) -> List[Tuple[str, str]]``.
"""

from __future__ import annotations

from typing import List, Mapping, Optional, Sequence, Tuple

from ..lexicon import Lexicon
from ..mwe.models import MWEToken
from .candidates import lookup_candidates
from .disambiguator import disambiguate


class POSTagger:
    """Filter-based rule POS tagger: candidates → rules → final tags."""

    def __init__(self, lexicon: Lexicon):
        self._lexicon = lexicon

    def tag(
        self,
        words: Sequence[str],
        *,
        mwe: Optional[Sequence[MWEToken]] = None,
        mwe_pos: Optional[Mapping[int, str]] = None,
    ) -> List[Tuple[str, str]]:
        """Tag *words*, optionally forcing POS at BMWE-merged indices.

        Pass either ``mwe`` (uses each span's ``index`` + ``resolved_pos()``)
        or an explicit ``mwe_pos`` map of ``merged_index → tag``.
        """
        words = list(words)
        if not words:
            return []
        candidates = [lookup_candidates(w, self._lexicon) for w in words]

        overrides = dict(mwe_pos) if mwe_pos else {}
        if mwe:
            for span in mwe:
                idx = span.index
                if idx is None:
                    continue
                if 0 <= idx < len(candidates):
                    overrides[idx] = span.resolved_pos()
        for idx, pos in overrides.items():
            if 0 <= idx < len(candidates):
                candidates[idx] = {pos}

        tags = disambiguate(words, candidates)
        return list(zip(words, tags))
