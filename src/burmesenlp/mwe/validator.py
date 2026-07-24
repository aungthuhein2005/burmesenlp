"""MWE validation hooks (V1: accept all)."""

from __future__ import annotations

from typing import Protocol, Sequence

from .models import MWEEntry


class MWEValidator(Protocol):
    def validate(
        self,
        entry: MWEEntry,
        context_tokens: Sequence[str],
        start: int,
    ) -> bool:
        ...


class AcceptAllValidator:
    """V1 stub — always accepts. Replace for POS/grammar checks later."""

    def validate(
        self,
        entry: MWEEntry,
        context_tokens: Sequence[str],
        start: int,
    ) -> bool:
        return True
