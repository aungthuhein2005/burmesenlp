"""Backward-compatible shim — prefer ``burmesenlp.tokenize.sentence``."""

from ..tokenize.sentence import Sentence, SentenceSegmenter

__all__ = ["Sentence", "SentenceSegmenter"]
