# -*- coding: utf-8 -*-
"""Throwaway port of Google myanmar-tools' bigram Markov Zawgyi detector
(Apache-2.0, https://github.com/google/myanmar-tools), used ONLY to
empirically validate the detector-approach design decision before writing
any production code. Not wired into burmesenlp.

Ported from clients/python/src/myanmartools/{_params.py,zawgyi_detector.py}
at commit reachable via the `master` branch, using the trained
zawgyiUnicodeModel.dat shipped in that repo (same .dat across all language
clients).
"""
from __future__ import annotations

import struct
from array import array
from bisect import bisect_left
from itertools import chain, repeat
from math import exp, inf, isnan, nan

STD = range(0x1000, 0x103F + 1)
AFT = range(0x104A, 0x109F + 1)
EXA = range(0xAA60, 0xAA7F + 1)
EXB = range(0xA9E0, 0xA9FF + 1)
SPC = range(0x2000, 0x200B + 1)


def _read_short(s):
    return struct.unpack(">h", s.read(2))[0]


def _read_int(s):
    return struct.unpack(">i", s.read(4))[0]


def _read_float(s):
    return struct.unpack(">f", s.read(4))[0]


def _read_pairs(s, n):
    return struct.iter_unpack(">hf", s.read(6 * n))


def _check_signature(stream):
    if stream.read(8) != b"UZMODEL ":
        raise IOError("invalid uzmodel_tag")
    version = _read_int(stream)
    ssv = 0 if version == 1 else _read_int(stream) if version == 2 else None
    if ssv is None:
        raise IOError("invalid uzmodel_version")
    if ssv == 0:
        chars = "".join(map(chr, chain(STD, AFT, EXA, EXB, SPC)))
    elif ssv == 1:
        chars = "".join(map(chr, chain(STD, AFT, EXA, EXB)))
    else:
        raise ValueError("invalid ssv")
    if stream.read(8) != b"BMARKOV ":
        raise IOError("invalid bmarkov_tag")
    if _read_int(stream) != 0:
        raise IOError("invalid bmarkov_version")
    return chars


def _read_params(stream):
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
    def __init__(self, model_path):
        with open(model_path, "rb") as f:
            self._chars = _check_signature(f)
            self._params = _read_params(f)
            self._params[0] = nan

    def _state(self, char):
        if char is None:
            return 0
        i = bisect_left(self._chars, char)
        if i < len(self._chars) and self._chars[i] == char:
            return i + 1
        return 0

    def pairwise_llrs(self, string):
        """Return [(char_before, char_after, llr), ...] for every adjacent
        pair, including boundary pairs with None. This is what the ported
        model gives us "for free" for free that the old is_zawgyi() heuristic
        cannot: a per-position score, not just a whole-string verdict."""
        size = len(self._chars) + 1
        left = chain((None,), string)
        right = chain(string, (None,))
        out = []
        for a, b in zip(left, right):
            llr = self._params[self._state(a) * size + self._state(b)]
            out.append((a, b, llr))
        return out

    def get_zawgyi_probability(self, string):
        llrs = [x[2] for x in self.pairwise_llrs(string)]
        if all(isnan(v) for v in llrs):
            return -inf
        total = sum(v for v in llrs if not isnan(v))
        if total >= 0:
            z = exp(-total)
            return z / (z + 1)
        return 1 / (1 + exp(total))


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    sys.path.insert(0, "src")
    from burmesenlp.zawgyi import is_zawgyi

    det = ZawgyiDetector("research/zawgyi-repair-log/zawgyiUnicodeModel.dat")

    UNICODE_SAMPLE = "မြန်မာစာပေ"
    ZAWGYI_SAMPLE = "ျမန္မာစာေပ"
    with open("research/zawgyi-repair-log/shan_sample.txt", encoding="utf-8") as f:
        SHAN_SAMPLE = f.read()

    for name, text in [
        ("clean Unicode Burmese", UNICODE_SAMPLE),
        ("clean Zawgyi Burmese", ZAWGYI_SAMPLE),
        ("genuine Shan (Wikipedia)", SHAN_SAMPLE),
    ]:
        p = det.get_zawgyi_probability(text)
        old = is_zawgyi(text)
        print(f"{name}:")
        print(f"  ported bigram model  P(zawgyi) = {p:.4f}")
        print(f"  current is_zawgyi()  verdict   = {old}")
        print()
