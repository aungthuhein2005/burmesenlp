"""Degree / attributive modifier rules."""

from __future__ import annotations

from .base import Rule, keep_only

MODIFIER_RULES = [
    Rule(
        name="ပို_before_verb_is_adv",
        priority=80,
        when=lambda ctx: (
            ctx.curr == "ပို"
            and "VERB" in ctx.nxt_cands()
            and bool(ctx.candidates[ctx.index] & {"ADV", "ADJ"})
        ),
        action=keep_only("ADV"),
    ),
    Rule(
        name="adj_before_noun",
        priority=78,
        when=lambda ctx: (
            {"NOUN", "ADJ"} <= ctx.candidates[ctx.index]
            and "NOUN" in ctx.nxt_cands()
            and "VERB" not in ctx.nxt_cands()
        ),
        action=keep_only("ADJ"),
    ),
]
