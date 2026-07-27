"""Noun / NP-licensing context rules."""

from __future__ import annotations

from ... import grammar
from .base import Rule, keep

_NP_MARKERS = frozenset({"ကို", "မှ", "သို့", "အား", "မှာ", "၌", "တွင်", "ရဲ့"})

NOUN_RULES = [
    Rule(
        name="before_object_marker",
        priority=90,
        when=lambda ctx: ctx.nxt == "ကို" and bool(
            ctx.candidates[ctx.index] & {"NOUN", "PRON", "NUM"}
        ),
        action=keep({"NOUN", "PRON", "NUM"}),
    ),
    Rule(
        name="before_ablative",
        priority=89,
        when=lambda ctx: ctx.nxt == "မှ" and "NOUN" in ctx.candidates[ctx.index],
        action=keep({"NOUN", "PRON", "NUM"}),
    ),
    Rule(
        name="before_allative",
        priority=89,
        when=lambda ctx: ctx.nxt == "သို့" and bool(
            ctx.candidates[ctx.index] & {"NOUN", "PRON"}
        ),
        action=keep({"NOUN", "PRON"}),
    ),
    Rule(
        name="before_အား",
        priority=89,
        when=lambda ctx: ctx.nxt == "အား" and bool(
            ctx.candidates[ctx.index] & {"NOUN", "PRON"}
        ),
        action=keep({"NOUN", "PRON"}),
    ),
    Rule(
        name="before_np_case_marker",
        priority=88,
        when=lambda ctx: (
            ctx.nxt in _NP_MARKERS
            and bool(ctx.candidates[ctx.index] & {"NOUN", "PRON", "NUM", "VERB"})
        ),
        action=keep({"NOUN", "PRON", "NUM"}),
    ),
    Rule(
        name="before_noun_suffix",
        priority=87,
        when=lambda ctx: (
            ctx.nxt in grammar.NOUN_SUFFIXES
            and "NOUN" in ctx.candidates[ctx.index]
        ),
        action=keep({"NOUN"}),
    ),
    # VERB/NOUN ambiguous head + plural တွေ/များ → noun reading (observers,
    # analysts, …). Lexicon must list NOUN; without it this never fires.
    Rule(
        name="verb_noun_before_plural_is_noun",
        priority=91,
        when=lambda ctx: (
            {"VERB", "NOUN"} <= ctx.candidates[ctx.index]
            and ctx.nxt in ("တွေ", "များ", "တို့")
        ),
        action=keep({"NOUN"}),
    ),
]
