"""Word-specific and closed-class ambiguity filters."""

from __future__ import annotations

from ... import grammar
from ...tokenize.syllable import FULL_STOP
from .base import Rule, keep_only

_NPISH = frozenset({"NOUN", "PRON", "NUM", "FW"})
_TERMINAL = frozenset(".!?\u2026")


def _npish(tags) -> bool:
    return bool(tags & _NPISH) or (
        bool(tags) and tags <= {"NOUN", "VERB"} and "NOUN" in tags
    )


def _is_terminal_punct(text: str) -> bool:
    return bool(text) and all(c in _TERMINAL for c in text)


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
            and ctx.curr not in ("သည်", "တယ်")
        ),
        action=lambda tags, ctx: (
            {"PART"} if ctx.nxt is None or ctx.nxt == FULL_STOP else {"POSTP"}
        )
        & tags,
    ),
    # Finite particles → SFP only in a verb-phrase tail
    # (VERB/AUX/PART + သည်/တယ် …).  Subject-marker reading is handled below.
    Rule(
        name="finite_particle_after_verb_is_sfp",
        priority=88,
        when=lambda ctx: (
            ctx.curr in grammar.FINITE_VERB_PARTICLES
            and "SFP" in ctx.candidates[ctx.index]
            and bool(ctx.prev_cands() & {"VERB", "AUX", "PART", "IDIOM"})
        ),
        action=keep_only("SFP"),
    ),
    # NOUN/PRON + သည် + NP-ish → subject/topic marker (POSTP), not SFP.
    # Example: ကျွန်တော်တို့သည် မြန်မာ… / သူသည် ကျောင်းကို…
    Rule(
        name="သည်_subject_marker_is_postp",
        priority=90,
        when=lambda ctx: (
            ctx.curr in ("သည်", "တယ်")
            and "POSTP" in ctx.candidates[ctx.index]
            and (
                _npish(ctx.prev_cands())
                or (ctx.prev is not None and ctx.prev in ("တို့", "များ", "တွေ"))
            )
            and ctx.nxt is not None
            and ctx.nxt != FULL_STOP
            and not _is_terminal_punct(ctx.nxt)
            and (
                _npish(ctx.nxt_cands())
                or bool(ctx.nxt_cands() & {"ADJ", "ADV", "NUM", "VERB", "IDIOM"})
            )
        ),
        action=keep_only("POSTP"),
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
    # NOUN/VERB-ambiguous word immediately before an AUX → must be VERB
    # (an auxiliary can only attach to a verbal stem). Fixes cases like
    # ပညာသင် + ခဲ့ where ပညာသင် was defaulting to NOUN via TAG_PREFERENCE.
    Rule(
        name="ambiguous_noun_verb_before_aux",
        priority=91,
        when=lambda ctx: (
            {"NOUN", "VERB"} <= ctx.candidates[ctx.index]
            and "AUX" in ctx.nxt_cands()
        ),
        action=keep_only("VERB"),
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
        name="ကတော့_after_np_is_postp",
        priority=83,
        when=lambda ctx: (
            ctx.curr == "ကတော့"
            and (
                _npish(ctx.prev_cands())
                or (ctx.prev is not None and ctx.prev in ("တို့", "များ", "တွေ"))
            )
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
                or ctx.nxt in ("က", "ကို", "မှာ", "မှ", "သို့", "အား", "သည်")
            )
        ),
        action=keep_only("PRON"),
    ),
]
