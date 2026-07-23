"""Conjunction vs postposition disambiguation (e.g. နှင့်)."""

from __future__ import annotations

from .base import Rule, keep_only

_NPISH = frozenset({"NOUN", "PRON", "NUM"})


def _npish(tags) -> bool:
    """True for clear NP tags (not verb-ambiguous open class)."""
    return bool(tags & _NPISH) and "VERB" not in tags


def _verbish(tags) -> bool:
    return "VERB" in tags


CONJUNCTION_RULES = [
    Rule(
        name="နှင့်_between_nouns_is_conj",
        priority=85,
        when=lambda ctx: (
            ctx.curr in ("နှင့်", "နဲ့")
            and _npish(ctx.prev_cands())
            and _npish(ctx.nxt_cands())
            and bool(ctx.candidates[ctx.index] & {"CONJ", "POSTP"})
        ),
        action=keep_only("CONJ"),
    ),
    Rule(
        name="နှင့်_before_verb_is_postp",
        priority=84,
        when=lambda ctx: (
            ctx.curr in ("နှင့်", "နဲ့")
            and _npish(ctx.prev_cands())
            and _verbish(ctx.nxt_cands())
            and "POSTP" in ctx.candidates[ctx.index]
        ),
        action=keep_only("POSTP"),
    ),
]
