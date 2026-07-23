"""Assemble all contextual / grammar rules (sorted by priority)."""

from __future__ import annotations

from typing import List

from .ambiguity import AMBIGUITY_RULES
from .base import Rule, SequenceRule
from .conjunction import CONJUNCTION_RULES
from .grammar import GRAMMAR_RULES
from .modifier import MODIFIER_RULES
from .noun import NOUN_RULES
from .verb import VERB_RULES

CONTEXT_RULES: List[Rule] = sorted(
    [
        *VERB_RULES,
        *NOUN_RULES,
        *CONJUNCTION_RULES,
        *MODIFIER_RULES,
        *AMBIGUITY_RULES,
    ],
    key=lambda r: r.priority,
    reverse=True,
)

SEQUENCE_RULES: List[SequenceRule] = sorted(
    GRAMMAR_RULES,
    key=lambda r: r.priority,
    reverse=True,
)

__all__ = ["CONTEXT_RULES", "SEQUENCE_RULES", "Rule", "SequenceRule"]
