"""Apply priority-ordered rules to eliminate impossible POS candidates."""

from __future__ import annotations

from typing import List, Sequence, Set

from ..lexicon import TAG_PREFERENCE
from .rules import CONTEXT_RULES, SEQUENCE_RULES
from .rules.base import TokenContext

TagSet = Set[str]


def _prefer(tags: TagSet) -> str:
    known = {t for t in tags if t in TAG_PREFERENCE}
    if not known:
        return next(iter(tags))
    return min(known, key=TAG_PREFERENCE.index)


def disambiguate(words: Sequence[str], candidates: List[TagSet]) -> List[str]:
    """Filter *candidates* in place via context then grammar rules; return final tags."""
    words = list(words)
    n = len(words)
    if n == 0:
        return []

    # --- Context rules (per token, high priority first) ---
    for i in range(n):
        ctx = TokenContext(words=words, index=i, candidates=candidates)
        for rule in CONTEXT_RULES:
            if not rule.when(ctx):
                continue
            narrowed = rule.action(candidates[i], ctx)
            if narrowed:
                candidates[i] = narrowed
            # refresh ctx.candidates reference is same list; ok

    # --- Grammar / sequence rules (left-to-right, non-overlapping prefer) ---
    i = 0
    while i < n:
        matched = False
        for rule in SEQUENCE_RULES:
            start = rule.match(words, candidates, i)
            if start is None:
                continue
            patches = rule.filters(start)
            for idx, allowed in patches.items():
                if 0 <= idx < n:
                    narrowed = candidates[idx] & set(allowed)
                    if narrowed:
                        candidates[idx] = narrowed
            # advance past the longest patch end
            end = max(patches) + 1 if patches else i + 1
            i = max(end, i + 1)
            matched = True
            break
        if not matched:
            i += 1

    return [_prefer(c) if c else "UNK" for c in candidates]
