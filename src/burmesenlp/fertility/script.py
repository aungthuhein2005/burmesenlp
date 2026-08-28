# -*- coding: utf-8 -*-
"""Script-run segmentation for per-script fertility reporting.

No third-party dependency: a hand-rolled codepoint classifier, not
``regex``'s ``\\p{Script}`` -- the category set here is deliberately
narrower than full Unicode Script (five buckets, not ~160), and pulling
in a dependency for this would be backwards given the whole point of the
``fertility`` extra split is to keep everything *except* the tokenizer
backends dependency-free.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import List, Tuple

_MYANMAR_RANGES = (
    (0x1000, 0x109F),  # Myanmar
    (0xA9E0, 0xA9FF),  # Myanmar Extended-B
    (0xAA60, 0xAA7F),  # Myanmar Extended-A
)
_LATIN_RANGES = (
    (0x0041, 0x005A),
    (0x0061, 0x007A),
    (0x00C0, 0x024F),  # Latin-1 Supplement letters onward, Latin Extended-A/B
)
_DIGIT_RANGES = (
    (0x0030, 0x0039),  # ASCII digits
    (0x1040, 0x1049),  # Myanmar digits
    (0x1090, 0x1099),  # Myanmar Shan digits
)

_SCRIPTS = ("myanmar", "latin", "digit", "whitespace", "punctuation", "other")


def _in_ranges(cp: int, ranges: "Tuple[Tuple[int, int], ...]") -> bool:
    return any(lo <= cp <= hi for lo, hi in ranges)


def _classify_char(ch: str) -> str:
    cp = ord(ch)
    # Digit check first: Myanmar digit codepoints (U+1040-1049) fall inside
    # the Myanmar block range too, but behave nothing like Myanmar letters
    # under BPE (small closed set, usually single-token even in
    # English-centric vocabularies) -- folding them into "myanmar" would
    # muddy the letter-fertility signal, which is the number that matters.
    if _in_ranges(cp, _DIGIT_RANGES):
        return "digit"
    # Myanmar punctuation (U+104A, U+104B) sits inside the main Myanmar
    # block range but is punctuation, not a letter -- must be checked
    # before the general Myanmar-range test, same reasoning as digits.
    if cp in (0x104A, 0x104B) or unicodedata.category(ch).startswith("P"):
        return "punctuation"
    if _in_ranges(cp, _MYANMAR_RANGES):
        return "myanmar"
    if _in_ranges(cp, _LATIN_RANGES):
        return "latin"
    if ch.isspace():
        return "whitespace"
    return "other"


@dataclass(frozen=True)
class ScriptRun:
    """A maximal run of same-category characters, plus any whitespace
    immediately preceding it (see ``segment_script_runs``)."""

    script: str
    text: str
    start: int
    end: int


def segment_script_runs(text: str) -> List[ScriptRun]:
    """Split *text* into runs of Myanmar / Latin / digit / punctuation /
    whitespace / other codepoints.

    A run of whitespace immediately before a non-whitespace run is
    attributed to the *following* run, not left standalone. This matches
    how BPE tokenizers actually spend a token: in every tokenizer checked
    here, a leading space merges into the following word as one token
    (e.g. ``' GDP'`` is a single token, not ``' '`` + ``'GDP'``) --
    counting the space against the run whose token it rides along with
    keeps the per-script token attribution honest instead of splitting a
    real token's cost across two buckets.
    """
    if not text:
        return []

    categories = [_classify_char(ch) for ch in text]
    runs: List[ScriptRun] = []
    i = 0
    n = len(text)
    while i < n:
        if categories[i] == "whitespace":
            ws_start = i
            j = i
            while j < n and categories[j] == "whitespace":
                j += 1
            if j >= n:
                # Trailing whitespace with nothing to attach to: its own run.
                runs.append(ScriptRun("whitespace", text[ws_start:j], ws_start, j))
                i = j
                continue
            # Attach to the run that starts at j.
            cat = categories[j]
            k = j
            while k < n and categories[k] == cat:
                k += 1
            runs.append(ScriptRun(cat, text[ws_start:k], ws_start, k))
            i = k
        else:
            cat = categories[i]
            j = i
            while j < n and categories[j] == cat:
                j += 1
            runs.append(ScriptRun(cat, text[i:j], i, j))
            i = j
    return runs


__all__ = ["ScriptRun", "segment_script_runs"]
