"""Burmese-to-Latin romanization.

Opt-in, separate entry point -- does not affect ``normalize()`` or
``process()``. See :mod:`burmesenlp.transliterate.bgn_pcgn` for the
system implemented (BGN/PCGN, the 1970 US/UK-agreed place-name-oriented
standard), its verified source, and what it deliberately does not
attempt in this v1.
"""
from .bgn_pcgn import romanize

__all__ = ["romanize"]
