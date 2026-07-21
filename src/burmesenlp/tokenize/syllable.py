"""Deterministic syllable tokenization for Myanmar text.

Follows the widely used "sylbreak" convention (Ye Kyaw Thu et al.): a
syllable boundary is placed before every consonant that is

  * not preceded by the stack virama (U+1039), and
  * not followed by asat (U+103A) or the stack virama.

Consequences of this convention:

  * Final consonants stay attached: "မြန်မာ" -> ["မြန်", "မာ"].
  * Kinzi sequences stay intact:    "အင်္ဂါ" -> ["အင်္ဂါ"].
  * Stacked (Pali) clusters stay attached to the preceding syllable:
    "မန္တလေး" -> ["မန္တ", "လေး"].

All offsets in the returned tokens refer to the string that was passed
in, which is expected to be already normalized (see ``normalize``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

from ..normalize import normalize

# Token kinds
SYLLABLE = "syllable"
DIGITS = "digits"
PUNCT = "punct"
OTHER = "other"

# Character constants (single code points)
ASAT = "\u103a"          # ်  kills the inherent vowel
STACK_VIRAMA = "\u1039"  # ္  subscripts the next consonant
ANUSVARA = "\u1036"      # ံ  nasalization
SECTION = "\u104a"       # ၊  little pause
FULL_STOP = "\u104b"     # ။  sentence-final stop

TONES = frozenset("\u1037\u1038")                      # ့ း
MEDIALS = frozenset("\u103b\u103c\u103d\u103e")        # ျ ြ ွ ှ
VOWEL_SIGNS = frozenset(
    "\u102b\u102c\u102d\u102e\u102f\u1030\u1031\u1032"  # ာ ါ ိ ီ ု ူ ေ ဲ
)
MY_DIGITS = frozenset("\u1040\u1041\u1042\u1043\u1044\u1045\u1046\u1047\u1048\u1049")

_ASCII_PUNCT = ".,;:!?()[]{}\"'\u2026\u201c\u201d\u2018\u2019"


@dataclass(frozen=True)
class Token:
    """A tokenized unit with character offsets into the normalized text."""

    text: str
    start: int
    end: int
    kind: str


# Split the input into Myanmar runs, whitespace runs, and everything else.
_RUNS = re.compile(r"[\u1000-\u109F]+|\s+|[^\u1000-\u109F\s]+")

# Positions where a new syllable begins inside a Myanmar run:
#   1. a consonant not preceded by the stack virama and not followed by
#      asat or the stack virama (the sylbreak rule)
#   2. an independent vowel or symbol (ဣ ဤ ဥ ဦ ဧ ဩ ဪ ၌ ၍ ၎ ၏)
#   3. the first digit of a digit run
#   4. Myanmar punctuation (၊ ။)
_BREAK = re.compile(
    "(?<!\u1039)[\u1000-\u1021](?![\u103A\u1039])"
    "|[\u1023-\u102A\u104C-\u104F]"
    "|(?<![\u1040-\u1049])[\u1040-\u1049]"
    "|[\u104A\u104B]"
)

# Inside non-Myanmar runs, separate ASCII/typographic punctuation.
_OTHER_SPLIT = re.compile(
    f"[{re.escape(_ASCII_PUNCT)}]+|[^{re.escape(_ASCII_PUNCT)}]+"
)


def _myanmar_kind(piece: str) -> str:
    if all(c in MY_DIGITS for c in piece):
        return DIGITS
    if all(c in (SECTION, FULL_STOP) for c in piece):
        return PUNCT
    return SYLLABLE


def tokenize(text: str) -> List[Token]:
    """Tokenize *already-normalized* text into syllable-level tokens.

    Returns tokens with (start, end) offsets into ``text``.  Whitespace
    is skipped (it never appears inside a token).
    """
    tokens: List[Token] = []
    for run_match in _RUNS.finditer(text):
        run = run_match.group(0)
        base = run_match.start()
        if run.isspace():
            continue
        first = run[0]
        if "\u1000" <= first <= "\u109f":
            starts = sorted({0} | {m.start() for m in _BREAK.finditer(run)})
            for idx, s in enumerate(starts):
                e = starts[idx + 1] if idx + 1 < len(starts) else len(run)
                piece = run[s:e]
                tokens.append(
                    Token(piece, base + s, base + e, _myanmar_kind(piece))
                )
        else:
            for m in _OTHER_SPLIT.finditer(run):
                piece = m.group(0)
                kind = PUNCT if piece[0] in _ASCII_PUNCT else OTHER
                tokens.append(
                    Token(piece, base + m.start(), base + m.end(), kind)
                )
    return tokens


def syllable_segment(text: str) -> List[str]:
    """Normalize *text* and return its syllables (plus digit/punct/other tokens)."""
    return [t.text for t in tokenize(normalize(text))]


def syllable_tokenize(text: str) -> List[str]:
    """Public alias for syllable segmentation (engine API naming)."""
    return syllable_segment(text)
