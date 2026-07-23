"""Priority-ordered contextual rules for POS candidate filtering.

Rules do not assign tags — they *intersect* the candidate set with the
tags that remain possible given local context (PyThaiNLP-style).

Tagset uses uppercase labels (``VERB``, ``NOUN``, ``AUX``, ``SFP``, …).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, FrozenSet, Iterable, List, Optional, Set

# Uppercase BurmeseNLP v1 tags (NOUN, VERB, AUX, SFP, …).
TagSet = Set[str]


@dataclass(frozen=True)
class TokenContext:
    """Window around the token being filtered."""

    words: List[str]
    index: int
    candidates: List[TagSet]

    @property
    def curr(self) -> str:
        return self.words[self.index]

    @property
    def prev(self) -> Optional[str]:
        return self.words[self.index - 1] if self.index > 0 else None

    @property
    def nxt(self) -> Optional[str]:
        i = self.index
        return self.words[i + 1] if i + 1 < len(self.words) else None

    def prev_cands(self) -> TagSet:
        return self.candidates[self.index - 1] if self.index > 0 else set()

    def nxt_cands(self) -> TagSet:
        i = self.index
        return self.candidates[i + 1] if i + 1 < len(self.candidates) else set()


WhenFn = Callable[[TokenContext], bool]
ActionFn = Callable[[TagSet, TokenContext], TagSet]


@dataclass(frozen=True)
class Rule:
    """A single candidate-filter rule.

    ``action`` must return a non-empty subset of the input tags when possible;
    an empty result is ignored so a bad rule cannot wipe all candidates.
    """

    name: str
    priority: int
    when: WhenFn
    action: ActionFn


def keep(allowed: Iterable[str]) -> ActionFn:
    """Build an action that intersects candidates with *allowed* tags."""
    allowed_set: FrozenSet[str] = frozenset(allowed)

    def _action(tags: TagSet, _ctx: TokenContext) -> TagSet:
        return tags & allowed_set

    return _action


def keep_only(*tags: str) -> ActionFn:
    return keep(tags)


@dataclass(frozen=True)
class SequenceRule:
    """Multi-token grammar pattern that filters several positions at once.

    ``match`` returns the start index of a match, or ``None``.
    ``filters`` maps relative offsets → tags to keep (intersected).
    """

    name: str
    priority: int
    match: Callable[[List[str], List[TagSet], int], Optional[int]]
    filters: Callable[[int], dict]  # start -> {offset: frozenset/set of tags}
