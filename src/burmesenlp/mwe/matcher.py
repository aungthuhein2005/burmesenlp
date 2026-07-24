"""Select the best MWE candidate among trie hits."""

from __future__ import annotations

from typing import Sequence

from .models import MWEEntry


def choose(candidates: Sequence[MWEEntry]) -> MWEEntry:
    """Pick best entry: highest priority, then longest, then first."""
    if not candidates:
        raise ValueError("choose() requires a non-empty candidate list")
    best = candidates[0]
    for cand in candidates[1:]:
        if cand.priority > best.priority:
            best = cand
        elif cand.priority == best.priority and len(cand.tokens) > len(best.tokens):
            best = cand
    return best
