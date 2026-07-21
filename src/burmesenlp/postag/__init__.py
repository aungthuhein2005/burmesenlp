"""Backward-compatible shim — prefer ``burmesenlp.tag.rule``."""

from ..tag.rule import POSTagger

__all__ = ["POSTagger"]
