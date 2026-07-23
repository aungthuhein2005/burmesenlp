"""Multi-token grammar / sentence-pattern rules."""

from __future__ import annotations

from typing import List, Optional, Set

from ... import grammar
from ...tokenize.syllable import FULL_STOP
from .base import SequenceRule

TagSet = Set[str]


def _verbish(cands: TagSet) -> bool:
    return "VERB" in cands or cands <= {"NOUN", "VERB"}


def _match_verb_aux_finite(
    words: List[str], cands: List[TagSet], start: int
) -> Optional[int]:
    if start + 2 >= len(words):
        return None
    if words[start + 1] not in grammar.VERB_AUXILIARIES:
        return None
    if words[start + 2] not in grammar.FINITE_VERB_PARTICLES:
        return None
    if not _verbish(cands[start]):
        return None
    return start


def _filters_verb_aux_finite(start: int) -> dict:
    return {
        start: frozenset({"VERB"}),
        start + 1: frozenset({"AUX"}),
        start + 2: frozenset({"SFP", "PART"}),
    }


def _match_verb_finite(
    words: List[str], cands: List[TagSet], start: int
) -> Optional[int]:
    if start + 1 >= len(words):
        return None
    if words[start + 1] not in grammar.FINITE_VERB_PARTICLES:
        return None
    if not _verbish(cands[start]):
        return None
    return start


def _filters_verb_finite(start: int) -> dict:
    return {
        start: frozenset({"VERB"}),
        start + 1: frozenset({"SFP", "PART"}),
    }


def _match_verb_aux_plural(
    words: List[str], cands: List[TagSet], start: int
) -> Optional[int]:
    if start + 2 >= len(words):
        return None
    if words[start + 1] not in ("ထား", "နေ"):
        return None
    if words[start + 2] != "ကြ":
        return None
    if not _verbish(cands[start]):
        return None
    return start


def _filters_verb_aux_plural(start: int) -> dict:
    return {
        start: frozenset({"VERB"}),
        start + 1: frozenset({"AUX"}),
        start + 2: frozenset({"PART"}),
    }


def _match_neg_verb(
    words: List[str], cands: List[TagSet], start: int
) -> Optional[int]:
    if words[start] != grammar.NEGATION_PARTICLE or start + 1 >= len(words):
        return None
    if not _verbish(cands[start + 1]):
        return None
    return start


def _filters_neg_verb(start: int) -> dict:
    return {
        start: frozenset({"PART"}),
        start + 1: frozenset({"VERB"}),
    }


def _match_finite_before_stop(
    words: List[str], cands: List[TagSet], start: int
) -> Optional[int]:
    if words[start] not in grammar.FINITE_VERB_PARTICLES:
        return None
    if start + 1 < len(words) and words[start + 1] == FULL_STOP:
        return start
    if start + 1 >= len(words):
        return start
    return None


def _filters_finite_sfp(start: int) -> dict:
    return {start: frozenset({"SFP", "PART"})}


GRAMMAR_RULES = [
    SequenceRule(
        name="verb_aux_finite",
        priority=96,
        match=_match_verb_aux_finite,
        filters=_filters_verb_aux_finite,
    ),
    SequenceRule(
        name="verb_aux_plural",
        priority=95,
        match=_match_verb_aux_plural,
        filters=_filters_verb_aux_plural,
    ),
    SequenceRule(
        name="verb_finite",
        priority=94,
        match=_match_verb_finite,
        filters=_filters_verb_finite,
    ),
    SequenceRule(
        name="negation_verb",
        priority=100,
        match=_match_neg_verb,
        filters=_filters_neg_verb,
    ),
    SequenceRule(
        name="finite_before_stop",
        priority=70,
        match=_match_finite_before_stop,
        filters=_filters_finite_sfp,
    ),
]
