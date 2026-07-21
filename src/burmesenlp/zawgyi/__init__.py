"""Zawgyi <-> Unicode conversion for Myanmar text."""

from .zawgyi import is_zawgyi, to_unicode, uni2zg, zg2uni

__all__ = ["uni2zg", "zg2uni", "is_zawgyi", "to_unicode"]
