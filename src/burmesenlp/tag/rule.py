"""Rule-based POS tagging with lexicon lookup and context disambiguation."""

from __future__ import annotations

from typing import List, Sequence, Tuple

from .. import grammar
from ..lexicon import Lexicon
from ..tokenize.syllable import FULL_STOP, MY_DIGITS, SECTION, tokenize

_ASCII_PUNCT = frozenset(".,;:!?()[]{}\"'\u2026\u201c\u201d\u2018\u2019")


def _is_myanmar_word(word: str) -> bool:
    return any("\u1000" <= c <= "\u109f" for c in word)


def _is_numeral_classifier(word: str) -> bool:
    """True for numeral/digit + counter merges such as သုံးခု or ၁၂၃ယောက်."""
    for classifier in grammar.COUNTER_CLASSIFIERS:
        if word.endswith(classifier) and len(word) > len(classifier):
            head = word[: -len(classifier)]
            if head in grammar.NUMERAL_WORDS or all(c in MY_DIGITS for c in head):
                return True
    return False


class POSTagger:
    def __init__(self, lexicon: Lexicon):
        self._lexicon = lexicon

    def tag(self, words: Sequence[str]) -> List[Tuple[str, str]]:
        words = list(words)
        return [(w, self._tag_word(w, i, words)) for i, w in enumerate(words)]

    # -- core rules, in priority order --------------------------------------

    def _tag_word(self, word: str, i: int, ctx: List[str]) -> str:
        if not word:
            return "unk"
        if word in (SECTION, FULL_STOP) or all(c in _ASCII_PUNCT for c in word):
            return "punc"
        if word.isdigit():  # covers both ASCII and Myanmar digits
            return "num"

        tags = self._lexicon.tags(word)
        if tags:
            if len(tags) == 1:
                return tags[0]
            return self._disambiguate(word, tags, i, ctx)

        if not _is_myanmar_word(word):
            return "fw"
        if word in grammar.NUMERAL_WORDS or _is_numeral_classifier(word):
            return "num"
        if word in grammar.PPM_MARKERS:
            return "ppm"
        if word in grammar.CONJUNCTIONS:
            return "conj"
        if word in grammar.FINAL_PARTICLES or word in grammar.VERB_SUFFIXES:
            return "part"

        # Suffix analysis for unknown words: longest matching suffix wins.
        best_tag = None
        best_len = 0
        for suffix in grammar.NOUN_SUFFIXES:
            if word.endswith(suffix) and len(word) > len(suffix) > best_len:
                best_tag, best_len = "n", len(suffix)
        for suffix in grammar.VERB_SUFFIXES:
            if word.endswith(suffix) and len(word) > len(suffix) > best_len:
                best_tag, best_len = "v", len(suffix)
        if best_tag:
            return best_tag

        # Context inference
        if i > 0:
            prev_tag = self._quick_tag(ctx[i - 1])
            n_syl = len(tokenize(word))
            if prev_tag in ("n", "pron") and n_syl == 1:
                return "part"
            if prev_tag == "ppm" and n_syl >= 2:
                return "v"

        return "n"  # most frequent open-class default

    # -- ambiguity resolution -------------------------------------------------

    def _disambiguate(
        self, word: str, tags: Tuple[str, ...], i: int, ctx: List[str]
    ) -> str:
        tag_set = set(tags)
        prev = ctx[i - 1] if i > 0 else None
        nxt = ctx[i + 1] if i + 1 < len(ctx) else None

        # part / ppm (e.g. ၏: sentence-final particle vs possessive marker)
        if {"part", "ppm"} <= tag_set:
            if nxt is None or nxt == FULL_STOP:
                return "part"
            return "ppm"

        # n / v
        if {"n", "v"} <= tag_set:
            if prev is not None and prev in grammar.PPM_MARKERS:
                return "v"
            if nxt is not None:
                if nxt in grammar.VERB_SUFFIXES or nxt in grammar.FINAL_PARTICLES:
                    return "v"
                if nxt in grammar.NOUN_SUFFIXES:
                    return "n"
            return "n"

        # n / adj
        if {"n", "adj"} <= tag_set:
            if nxt is not None and self._quick_tag(nxt) == "n":
                return "adj"
            return "n"

        # pron / n
        if {"pron", "n"} <= tag_set:
            if i == 0:
                return "pron"
            if prev is not None and prev in grammar.PPM_MARKERS:
                return "pron"
            if nxt is not None and nxt in grammar.PPM_MARKERS:
                return "pron"
            return "n"

        return tags[0]  # stored in TAG_PREFERENCE order

    def _quick_tag(self, word: str) -> str:
        tags = self._lexicon.tags(word)
        if tags:
            return tags[0]
        if word in grammar.PPM_MARKERS:
            return "ppm"
        if word in grammar.CONJUNCTIONS:
            return "conj"
        if word in grammar.VERB_SUFFIXES:
            return "part"
        return "n"
