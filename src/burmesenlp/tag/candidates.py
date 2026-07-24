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

    tags = set(lexicon.tags(word) or [])

    # Closed-class augmentations always apply (even when the lexicon
    # already lists a default tag).  သည် / တယ် are both subject markers
    # (POSTP) and sentence-final particles (SFP) depending on context.
    if word in grammar.FINAL_PARTICLES or word in grammar.FINITE_VERB_PARTICLES:
        tags.update({"SFP", "PART"})
    if word in ("သည်", "တယ်"):
        tags.add("POSTP")
    if word in grammar.PPM_MARKERS:
        tags.add("POSTP")
    if word in grammar.CONJUNCTIONS:
        tags.add("CONJ")
    if word in grammar.VERB_AUXILIARIES:
        tags.add("AUX")
    if word in grammar.VERB_SUFFIXES or word == grammar.NEGATION_PARTICLE:
        tags.add("PART")
    if word in ("နှင့်", "နဲ့"):
        tags.update({"POSTP", "CONJ"})

    if tags:
        return tags

    out: Set[str] = set()
    if not _is_myanmar_word(word):
        return {"FW"}
    if word in grammar.NUMERAL_WORDS or _is_numeral_classifier(word):
        out.add("NUM")

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
