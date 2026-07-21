"""Backward-compatible shim — prefer ``burmesenlp.tokenize.longest``."""

from ..tokenize.longest import WORD, WordSegmenter

__all__ = ["WORD", "WordSegmenter"]
