# -*- coding: utf-8 -*-
"""
Zawgyi <-> Unicode conversion for Myanmar text.

Conversion rules are adapted from the Rabbit converter project
(https://github.com/Rabbit-Converter/Rabbit, WTFPL license), restructured
here so that:

  - Rules are loaded from JSON and compiled to ``re.Pattern`` objects once
    at first use, instead of being re-parsed on every call.
  - A lightweight ``is_zawgyi()`` heuristic detector is provided.
  - ``to_unicode()`` detects, converts only if needed, then NFC-normalizes.

Detection combines three signals:

  1. Codepoints in Myanmar Extended-A (U+1060-U+1097) and U+105A that
     Zawgyi reuses for glyph variants.
  2. U+1039 (virama) not followed by a consonant — Zawgyi's visible asat.
  3. Visual-order tells: vowel-e (U+1031) or medial-ya (U+103B) appearing
     before a base consonant (common Zawgyi rendering order).

This is a fast heuristic, not a statistical classifier. For messy corpora,
pair with a second opinion (e.g. Google myanmar-tools) when stakes are high.
"""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import List, Pattern, Tuple

_DATA_DIR = Path(__file__).parent

_ZAWGYI_INDICATOR_RANGE = range(0x1060, 0x1098)  # U+1060 - U+1097
_ZAWGYI_INDICATOR_EXTRA = {0x105A}

_VIRAMA = 0x1039
_CONSONANT_RANGE = range(0x1000, 0x1022)  # U+1000 - U+1021

# Visual-order / structure hints (shared idea with normalize.looks_like_zawgyi).
_ZAWGYI_ORDER = re.compile(
    "[\u105a\u1060-\u1097]"
    "|(?:^|[^\u1000-\u1021\u103a-\u103f])[\u1031\u103b]"
    "|\u1031\u1031"
    "|\u103a\u103a"
)


def _compile_rules(rules: List[dict]) -> List[Tuple[Pattern[str], str]]:
    """Compile a list of {"from": pattern, "to": replacement} dicts once."""
    compiled: List[Tuple[Pattern[str], str]] = []
    for rule in rules:
        compiled.append((re.compile(rule["from"]), rule["to"]))
    return compiled


@lru_cache(maxsize=1)
def _uni2zg_rules() -> List[Tuple[Pattern[str], str]]:
    with open(_DATA_DIR / "uni2zg_rules.json", encoding="utf-8") as f:
        return _compile_rules(json.load(f))


@lru_cache(maxsize=1)
def _zg2uni_rules() -> List[Tuple[Pattern[str], str]]:
    with open(_DATA_DIR / "zg2uni_rules.json", encoding="utf-8") as f:
        return _compile_rules(json.load(f))


def _apply_rules(text: str, rules: List[Tuple[Pattern[str], str]]) -> str:
    for pattern, replacement in rules:
        text = pattern.sub(replacement, text)
    return text


def uni2zg(text: str) -> str:
    """Convert standard Unicode Myanmar text to Zawgyi encoding."""
    if not isinstance(text, str):
        raise TypeError(f"expected str, got {type(text).__name__}")
    return _apply_rules(text, _uni2zg_rules())


def zg2uni(text: str) -> str:
    """Convert Zawgyi-encoded text to standard Unicode Myanmar."""
    if not isinstance(text, str):
        raise TypeError(f"expected str, got {type(text).__name__}")
    return _apply_rules(text, _zg2uni_rules())


def is_zawgyi(text: str) -> bool:
    """Heuristic check for whether *text* is Zawgyi-encoded."""
    if not isinstance(text, str):
        raise TypeError(f"expected str, got {type(text).__name__}")
    if not text:
        return False

    length = len(text)
    for i, ch in enumerate(text):
        cp = ord(ch)
        if cp in _ZAWGYI_INDICATOR_RANGE or cp in _ZAWGYI_INDICATOR_EXTRA:
            return True
        if cp == _VIRAMA:
            next_cp = ord(text[i + 1]) if i + 1 < length else None
            if next_cp not in _CONSONANT_RANGE:
                return True

    return bool(_ZAWGYI_ORDER.search(text))


def to_unicode(text: str, *, normalize: bool = True) -> str:
    """Ensure *text* is standard Unicode Myanmar.

    Detects Zawgyi and converts only if needed, then applies NFC by default.
    Safe to call on text of unknown encoding.
    """
    if not isinstance(text, str):
        raise TypeError(f"expected str, got {type(text).__name__}")
    if is_zawgyi(text):
        text = zg2uni(text)
    if normalize:
        text = unicodedata.normalize("NFC", text)
    return text


__all__ = ["uni2zg", "zg2uni", "is_zawgyi", "to_unicode"]
