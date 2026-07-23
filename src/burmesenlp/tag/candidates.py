"""Stage 1: collect candidate POS tags (no choice yet)."""

from __future__ import annotations

from typing import Set

from .. import grammar
from ..lexicon import Lexicon
from ..tokenize.syllable import FULL_STOP, MY_DIGITS, SECTION

_ASCII_PUNCT = frozenset(".,;:!?()[]{}\"'\u2026\u201c\u201d\u2018\u2019")


def _is_myanmar_word(word: str) -> bool:
    return any("\u1000" <= c <= "\u109f" for c in word)


def _is_numeral_classifier(word: str) -> bool:
    for classifier in grammar.COUNTER_CLASSIFIERS:
        if word.endswith(classifier) and len(word) > len(classifier):
            head = word[: -len(classifier)]
            if head in grammar.NUMERAL_WORDS or all(c in MY_DIGITS for c in head):
                return True
    return False


def lookup_candidates(word: str, lexicon: Lexicon) -> Set[str]:
    """Return all plausible POS tags for *word* (lexicon + closed-class heuristics)."""
    if not word:
        return {"UNK"}
    if word in (SECTION, FULL_STOP) or all(c in _ASCII_PUNCT for c in word):
        return {"PUNCT"}
    if word.isdigit():
        return {"NUM"}

    tags = lexicon.tags(word)
    if tags:
        return set(tags)

    out: Set[str] = set()
    if not _is_myanmar_word(word):
        return {"FW"}
    if word in grammar.NUMERAL_WORDS or _is_numeral_classifier(word):
        out.add("NUM")
    if word in grammar.PPM_MARKERS:
        out.add("POSTP")
    if word in grammar.CONJUNCTIONS:
        out.add("CONJ")
    if word in grammar.FINAL_PARTICLES or word in grammar.FINITE_VERB_PARTICLES:
        out.add("SFP")
    if word in grammar.VERB_AUXILIARIES:
        out.add("AUX")
    if word in grammar.VERB_SUFFIXES or word == grammar.NEGATION_PARTICLE:
        out.add("PART")
    if word in ("နှင့်", "နဲ့"):
        out.update({"POSTP", "CONJ"})

    best_len = 0
    for suffix in grammar.NOUN_SUFFIXES:
        if word.endswith(suffix) and len(word) > len(suffix) >= best_len:
            out.add("NOUN")
            best_len = len(suffix)
    for suffix in grammar.VERB_SUFFIXES:
        if word.endswith(suffix) and len(word) > len(suffix) >= best_len:
            out.add("VERB")
            best_len = len(suffix)

    return out or {"NOUN", "VERB"}
