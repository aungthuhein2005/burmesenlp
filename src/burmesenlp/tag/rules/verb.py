"""Verb-licensing context rules (highest priority)."""

from __future__ import annotations

from ... import grammar
from .base import Rule, keep_only


def _has_verb(tags) -> bool:
    return "VERB" in tags or tags <= {"NOUN", "VERB"}


def _is_aux_reading(ctx) -> bool:
    """Auxiliary reading: verbal previous + aux word with ``AUX`` candidate."""
    return (
        ctx.curr in grammar.VERB_AUXILIARIES
        and "AUX" in ctx.candidates[ctx.index]
        and bool(ctx.prev_cands() & {"VERB"})
    )


VERB_RULES = [
    Rule(
        name="negation_licenses_verb",
        priority=100,
        when=lambda ctx: ctx.prev == grammar.NEGATION_PARTICLE and _has_verb(
            ctx.candidates[ctx.index]
        ),
        action=keep_only("VERB"),
    ),
    Rule(
        name="finite_particle_licenses_verb",
        priority=95,
        when=lambda ctx: (
            ctx.nxt in grammar.FINITE_VERB_PARTICLES
            and _has_verb(ctx.candidates[ctx.index])
            and not _is_aux_reading(ctx)
        ),
        action=keep_only("VERB"),
    ),
    Rule(
        name="aux_licenses_preceding_verb",
        priority=94,
        when=lambda ctx: (
            ctx.nxt in grammar.VERB_AUXILIARIES
            and _has_verb(ctx.candidates[ctx.index])
            and ctx.index + 2 < len(ctx.words)
            and ctx.words[ctx.index + 2] in grammar.FINITE_VERB_PARTICLES
        ),
        action=keep_only("VERB"),
    ),
    Rule(
        name="aux_or_suffix_after_ambiguous",
        priority=93,
        when=lambda ctx: (
            not _is_aux_reading(ctx)
            and ctx.curr not in grammar.VERB_AUXILIARIES
            and (
                ctx.nxt in grammar.VERB_AUXILIARIES
                or ctx.nxt in grammar.VERB_SUFFIXES
            )
            and "VERB" in ctx.candidates[ctx.index]
        ),
        action=keep_only("VERB"),
    ),
    Rule(
        name="after_postp_prefer_verb",
        priority=92,
        when=lambda ctx: (
            ctx.prev is not None
            and ctx.prev in grammar.PPM_MARKERS
            and "VERB" in ctx.candidates[ctx.index]
            and not _is_aux_reading(ctx)
        ),
        action=keep_only("VERB"),
    ),
]
