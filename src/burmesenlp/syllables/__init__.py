"""Backward-compatible shim — prefer ``burmesenlp.tokenize.syllable``."""

from ..tokenize.syllable import *  # noqa: F401,F403
from ..tokenize.syllable import (
    ANUSVARA,
    ASAT,
    DIGITS,
    FULL_STOP,
    MEDIALS,
    MY_DIGITS,
    OTHER,
    PUNCT,
    SECTION,
    STACK_VIRAMA,
    SYLLABLE,
    TONES,
    Token,
    VOWEL_SIGNS,
    syllable_segment,
    tokenize,
)

__all__ = [
    "ANUSVARA",
    "ASAT",
    "DIGITS",
    "FULL_STOP",
    "MEDIALS",
    "MY_DIGITS",
    "OTHER",
    "PUNCT",
    "SECTION",
    "STACK_VIRAMA",
    "SYLLABLE",
    "TONES",
    "Token",
    "VOWEL_SIGNS",
    "syllable_segment",
    "tokenize",
]
