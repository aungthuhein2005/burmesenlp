"""Word-specific and closed-class ambiguity filters."""

from __future__ import annotations

from ... import grammar
from ...tokenize.syllable import FULL_STOP
from .base import Rule, keep_only

_NPISH = frozenset({"NOUN", "PRON", "NUM", "FW"})


def _npish(tags) -> bool:
    return bool(tags & _NPISH) or (
        bool(tags) and tags <= {"NOUN", "VERB"} and "NOUN" in tags
    )


AMBIGUITY_RULES = [
    Rule(
        name="၏_final_is_part",
        priority=86,
        when=lambda ctx: (
            ctx.curr == "၏"
            and bool(ctx.candidates[ctx.index] & {"PART", "POSTP"})
            and (ctx.nxt is None or ctx.nxt == FULL_STOP)
        ),
        action=keep_only("PART"),
    ),
    Rule(
        name="၏_medial_is_postp",
        priority=86,
        when=lambda ctx: (
            ctx.curr == "၏"
            and bool(ctx.candidates[ctx.index] & {"PART", "POSTP"})
            and ctx.nxt is not None
            and ctx.nxt != FULL_STOP
        ),
        action=keep_only("POSTP"),
    ),
    Rule(
        name="part_postp_finality",
        priority=82,
        when=lambda ctx: (
            {"PART", "POSTP"} <= ctx.candidates[ctx.index]
            and ctx.curr != "၏"
        ),
        action=lambda tags, ctx: (
            {"PART"} if ctx.nxt is None or ctx.nxt == FULL_STOP else {"POSTP"}
        )
        & tags,
    ),
    # Finite particles → SFP when that candidate exists
    Rule(
        name="finite_particle_is_sfp",
        priority=88,
        when=lambda ctx: (
            ctx.curr in grammar.FINITE_VERB_PARTICLES
            and "SFP" in ctx.candidates[ctx.index]
        ),
        action=keep_only("SFP"),
    ),
    # Aux after a verb → AUX
    Rule(
        name="aux_after_verb",
        priority=97,
        when=lambda ctx: (
            ctx.curr in grammar.VERB_AUXILIARIES
            and bool(ctx.prev_cands() & {"VERB"})
            and "AUX" in ctx.candidates[ctx.index]
        ),
        action=keep_only("AUX"),
    ),
    Rule(
        name="က_after_np_is_postp",
        priority=83,
        when=lambda ctx: (
            ctx.curr == "က"
            and _npish(ctx.prev_cands())
            and "POSTP" in ctx.candidates[ctx.index]
        ),
        action=keep_only("POSTP"),
    ),
    Rule(
        name="pron_sentence_initial",
        priority=81,
        when=lambda ctx: (
            {"PRON", "NOUN"} <= ctx.candidates[ctx.index] and ctx.index == 0
        ),
        action=keep_only("PRON"),
    ),
    Rule(
        name="pron_before_or_after_postp",
        priority=81,
        when=lambda ctx: (
            {"PRON", "NOUN"} <= ctx.candidates[ctx.index]
            and (
                (ctx.prev is not None and "POSTP" in ctx.prev_cands())
                or (ctx.nxt is not None and "POSTP" in ctx.nxt_cands())
                or ctx.nxt in ("က", "ကို", "မှာ", "မှ", "သို့", "အား")
            )
        ),
        action=keep_only("PRON"),
    ),
]
