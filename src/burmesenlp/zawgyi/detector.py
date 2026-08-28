# -*- coding: utf-8 -*-
"""Calibrated Zawgyi/Unicode detector: a bigram Markov model over Myanmar
codepoint states, ported from Google's myanmar-tools.

Source: https://github.com/google/myanmar-tools
License: Apache-2.0 (compatible with this project's Apache-2.0 license;
see that repository's LICENSE.md).
Vendored files: ``zawgyiUnicodeModel.dat``, ported from
``clients/python/src/myanmartools/{_params.py,zawgyi_detector.py}`` at
commit 7d7f7316bd5f580112e308acd6dbd5d1be3e258f ("Retrain using new
multi-language model", 2020-07-20), present in the v1.2.0+ release family.
The port below is a from-scratch re-implementation of the same algorithm
against that data file, not a copy of Google's source files.

Why this exists alongside ``is_zawgyi()``: that heuristic is a fast,
single-codepoint-range check that is right most of the time but has a
real, measured blind spot -- it also matches Shan/Mon/Kayah/Karen/Rumai
Palaung letters, which share codepoints with Zawgyi's glyph-variant reuse
of that Unicode range (see CHANGELOG for measured false-positive rates on
real Wikipedia text). This model is a per-adjacent-character-pair bigram
likelihood, so it distinguishes genuine minority-language text from
Zawgyi by context instead of by codepoint membership alone.

This module is opt-in: importing ``burmesenlp.zawgyi`` does not load the
model. The 28KB data file is loaded lazily, once, on first use of
``get_zawgyi_probability()`` / ``score_paragraphs()``.
"""
from __future__ import annotations

import re
import struct
from array import array
from bisect import bisect_left
from functools import lru_cache
from itertools import chain, repeat
from math import exp, inf, isnan, nan
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

_DATA_DIR = Path(__file__).parent
_MODEL_PATH = _DATA_DIR / "zawgyiUnicodeModel.dat"

_STD = range(0x1000, 0x103F + 1)
_AFT = range(0x104A, 0x109F + 1)
_EXA = range(0xAA60, 0xAA7F + 1)
_EXB = range(0xA9E0, 0xA9FF + 1)
_SPC = range(0x2000, 0x200B + 1)

_PARAGRAPH_SPLIT = re.compile(r"(\n+)")


def _read_short(stream) -> int:
    return struct.unpack(">h", stream.read(2))[0]


def _read_int(stream) -> int:
    return struct.unpack(">i", stream.read(4))[0]


def _read_float(stream) -> float:
    return struct.unpack(">f", stream.read(4))[0]


def _read_pairs(stream, n: int):
    return struct.iter_unpack(">hf", stream.read(6 * n))


def _check_signature(stream) -> str:
    if stream.read(8) != b"UZMODEL ":
        raise IOError("invalid uzmodel_tag")
    version = _read_int(stream)
    if version == 1:
        ssv = 0
    elif version == 2:
        ssv = _read_int(stream)
    else:
        raise IOError("invalid uzmodel_version")

    if ssv == 0:
        chars = "".join(map(chr, chain(_STD, _AFT, _EXA, _EXB, _SPC)))
    elif ssv == 1:
        chars = "".join(map(chr, chain(_STD, _AFT, _EXA, _EXB)))
    else:
        raise ValueError("invalid ssv")

    if stream.read(8) != b"BMARKOV ":
        raise IOError("invalid bmarkov_tag")
    if _read_int(stream) != 0:
        raise IOError("invalid bmarkov_version")
    return chars


def _read_params(stream) -> "array[float]":
    size = _read_short(stream)
    params = array("f", repeat(0, size * size))
    for i in range(size):
        count = _read_short(stream)
        if count:
            offset = i * size
            value = _read_float(stream)
            for idx in range(size):
                params[offset + idx] = value
            for idx, value in _read_pairs(stream, count):
                params[offset + idx] = value
    return params


class ZawgyiDetector:
    """Bigram Markov Zawgyi/Unicode detector. See module docstring."""

    __slots__ = ["_chars", "_params"]

    def __init__(self, model_path: Path = _MODEL_PATH) -> None:
        with open(model_path, "rb") as stream:
            self._chars = _check_signature(stream)
            self._params = _read_params(stream)
            self._params[0] = nan

    def _state(self, char: Optional[str]) -> int:
        if char is None:
            return 0
        i = bisect_left(self._chars, char)
        if i < len(self._chars) and self._chars[i] == char:
            return i + 1
        return 0

    def pairwise_llrs(self, text: str) -> List[Tuple[Optional[str], Optional[str], float]]:
        """Log-likelihood ratios for every adjacent character pair,
        including the string boundaries (paired with ``None``)."""
        size = len(self._chars) + 1
        left = chain((None,), text)
        right = chain(text, (None,))
        return [
            (a, b, self._params[self._state(a) * size + self._state(b)])
            for a, b in zip(left, right)
        ]

    def get_zawgyi_probability(self, text: str) -> float:
        """Probability that *text* is Zawgyi-encoded, in [0, 1].
        Returns -inf if *text* has no characters the model has an opinion
        on (e.g. pure Latin text)."""
        llrs = [v for _, _, v in self.pairwise_llrs(text)]
        if all(isnan(v) for v in llrs):
            return -inf
        total = sum(v for v in llrs if not isnan(v))
        if total >= 0:
            z = exp(-total)
            return z / (z + 1)
        return 1 / (1 + exp(total))


@lru_cache(maxsize=1)
def _detector() -> ZawgyiDetector:
    return ZawgyiDetector()


def get_zawgyi_probability(text: str) -> float:
    """Calibrated Zawgyi probability for *text* (lazily loads the vendored
    model on first call)."""
    if not isinstance(text, str):
        raise TypeError(f"expected str, got {type(text).__name__}")
    return _detector().get_zawgyi_probability(text)


def split_paragraphs(text: str) -> List[str]:
    """Split *text* into scoring segments (paragraphs/lines), preserving
    enough structure to reassemble the document byte-for-byte around them.
    Returns the non-separator pieces only; use ``_split_with_separators``
    to reassemble."""
    return [p for p in _PARAGRAPH_SPLIT.split(text)[0::2] if p.strip()]


def _split_with_separators(text: str) -> List[str]:
    """Like ``_PARAGRAPH_SPLIT.split`` but keeps separators inline, so the
    pieces can be rejoined with ``"".join(...)`` to reproduce *text*
    exactly."""
    return _PARAGRAPH_SPLIT.split(text)


def score_paragraphs(text: str) -> Sequence[Tuple[str, float]]:
    """Return [(paragraph_text, zawgyi_probability), ...] for each
    non-blank paragraph/segment in *text*."""
    det = _detector()
    return [(p, det.get_zawgyi_probability(p)) for p in split_paragraphs(text)]


__all__ = [
    "ZawgyiDetector",
    "get_zawgyi_probability",
    "score_paragraphs",
    "split_paragraphs",
]
