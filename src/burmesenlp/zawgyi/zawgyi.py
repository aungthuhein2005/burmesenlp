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

``is_zawgyi()`` detection combines three signals:

  1. Codepoints in Myanmar Extended-A (U+1060-U+1097) and U+105A that
     Zawgyi reuses for glyph variants.
  2. U+1039 (virama) not followed by a consonant — Zawgyi's visible asat.
  3. Visual-order tells: vowel-e (U+1031) or medial-ya (U+103B) appearing
     before a base consonant (common Zawgyi rendering order).

This is a fast heuristic, not a statistical classifier, and it is
measurably wrong on minority-language text: signal 1's codepoint range is
also the Unicode block for Shan/Mon/Kayah/Karen/Rumai Palaung letters, so
any single character from those languages triggers a false "Zawgyi"
verdict. Measured on real Wikipedia text (paragraph-level): **Shan ~100%
false-positive rate (119/122), Mon ~72% (283/393)**. This is not a
narrow-range problem fixable by excluding a sub-block: the same
codepoints Zawgyi genuinely reuses for glyph variants (see zg2uni's rule
5, and the 14 rules mapping individual Karen-range codepoints to
stacked-consonant shorthand) ARE the minority-language letters --
authorial intent, not the codepoint, is what distinguishes them, which
is why only context-sensitive detection (below) can actually resolve
this rather than a differently-drawn range.

For that reason, ``to_unicode()`` no longer calls ``is_zawgyi()``
internally -- it uses :func:`burmesenlp.zawgyi.detector.get_zawgyi_probability`
(a bigram Markov model, scores 0.0 on both Shan/Mon samples above vs.
1.0 on confirmed Zawgyi text) instead, since a false positive here
silently destroys the input with no recovery path. ``is_zawgyi()``
itself is UNCHANGED and kept for callers who rely on its exact boolean
semantics; prefer ``get_zawgyi_probability()`` directly when the answer
matters (e.g. anything touching text that might be Shan/Mon/Karen).
"""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import List, Pattern, Tuple

from .detector import get_zawgyi_probability

_DATA_DIR = Path(__file__).parent

_ZAWGYI_INDICATOR_RANGE = range(0x1060, 0x1098)  # U+1060 - U+1097
_ZAWGYI_INDICATOR_EXTRA = {0x105A}

_VIRAMA = 0x1039
_CONSONANT_RANGE = range(0x1000, 0x1022)  # U+1000 - U+1021

# Visual-order / structure hints (shared idea with normalize.looks_like_zawgyi;
# the pattern text is identical, confirmed via .pattern ==, but this is an
# independent copy, not shared code).
#
# NOTE: this regex's own [\u105a\u1060-\u1097] alternative is unreachable
# from is_zawgyi() below -- that range is signal 1's per-character loop,
# which returns True before the loop can finish, so this regex is only
# ever evaluated on text where signal 1 already found nothing in that
# range. Only the other three alternatives (doubled vowel-e, doubled
# asat, vowel-e/medial-ya before a consonant) can actually contribute a
# verdict here; the range clause is dead code in this call path
# (confirmed empirically: 0/122 Shan and 0/393 Mon false positives came
# from this signal -- all Shan and 87.6% of Mon came from signal 1
# alone; see CHANGELOG for the rest of the Mon breakdown).
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
    """Heuristic check for whether *text* is Zawgyi-encoded.

    Fast, but NOT reliable on minority-language text: its codepoint-range
    signal is also the Unicode block for Shan/Mon/Kayah/Karen/Rumai
    Palaung letters, and there is no way to narrow that range to exclude
    them, because Zawgyi's own glyph-variant reuse and those languages'
    genuine letters are frequently the identical codepoint -- only
    authorial intent tells them apart, not the codepoint itself (see
    zg2uni's rule 5 and its 14 Karen-range rules). Measured false-positive
    rate on real Wikipedia text, paragraph-level: **Shan ~100%
    (119/122), Mon ~72% (283/393)**.

    For a calibrated answer, use
    :func:`burmesenlp.zawgyi.detector.get_zawgyi_probability` instead --
    it scores 0.0 on both samples above. This function is kept unchanged
    for callers who rely on its exact boolean semantics; ``to_unicode()``
    no longer calls it internally for exactly this reason (a false
    positive here has no recovery path -- see that function).
    """
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


DEFAULT_ZAWGYI_THRESHOLD = 0.9
"""Default probability threshold for :func:`to_unicode`.

Not 0.5: the cost of the two error directions is asymmetric. A false
positive here converts real Shan/Mon/Karen text through the full zg2uni
cascade and returns the mangled result with no recovery path -- that is
irreversible data loss. A false negative just leaves genuinely-Zawgyi
text unconverted, which is visible and recoverable (call zg2uni()
directly, or reprocess). That asymmetry justifies erring well above 0.5.

Calibrated from measurement, not picked blind: 0.9 sits comfortably
above the one real Mon Wikipedia paragraph that scored 0.756789 (the
highest of any confirmed-non-Zawgyi sample checked -- every Shan sample
scored effectively 0, ~1e-5 or below), while 6 of 8 real Zawgyi
sentences (Rabbit-Converter's own sample.json) score a clean 1.0. The
honest cost: at 0.9, one of those 8 real Zawgyi sentences (score 0.538)
moves from correctly-converted to a false negative it wouldn't have
been at the default 0.5 -- accepted deliberately, per the asymmetry
above, not overlooked. n=8 confirmed-Zawgyi examples is a small
calibration sample; revisit if a larger one becomes available.
"""


def to_unicode(text: str, *, normalize: bool = True, threshold: float = DEFAULT_ZAWGYI_THRESHOLD) -> str:
    """Ensure *text* is standard Unicode Myanmar.

    Detects Zawgyi and converts only if needed, then applies NFC by default.
    Safe to call on text of unknown encoding.

    Detection uses :func:`burmesenlp.zawgyi.detector.get_zawgyi_probability`
    (a bigram Markov model), NOT :func:`is_zawgyi` -- that heuristic's
    codepoint-range signal is also the Unicode block for Shan/Mon/Kayah/
    Karen/Rumai Palaung letters (see :func:`is_zawgyi`'s docstring for
    measured false-positive rates), and a false positive here is
    irreversible, unlike a false negative. See
    :data:`DEFAULT_ZAWGYI_THRESHOLD` for why the default isn't 0.5.
    """
    if not isinstance(text, str):
        raise TypeError(f"expected str, got {type(text).__name__}")
    if get_zawgyi_probability(text) > threshold:
        text = zg2uni(text)
    if normalize:
        text = unicodedata.normalize("NFC", text)
    return text


__all__ = ["uni2zg", "zg2uni", "is_zawgyi", "to_unicode"]
