# -*- coding: utf-8 -*-
"""Core fertility measurement: denominators, per-text results, and
distribution aggregation across a corpus.

CAVEATS ARE ATTACHED TO THE DATA, not just prose in a report -- both
``FertilityResult`` and the aggregate output carry a ``caveats`` list, so
anyone reading these numbers later (from a saved JSON file, say) gets the
warnings without having to find the surrounding writeup:

  1. Per-script-run token counts are each tokenizer run *independently*
     on that run's substring, which slightly overstates the true
     whole-document total (it can't find a BPE merge that would have
     spanned a script-run boundary). The whole-document count (the
     tokenizer run once, over the full text) is the number that matters
     for cost; per-run numbers are for the breakdown story only.
  2. Any English baseline used alongside these numbers is comparable-
     genre (same kind of prose), not parallel (translated) text -- it
     controls for register, not for matched information content.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from ..normalize import canonical_order
from ..normalize import normalize as _normalize_text
from .backends import TokenizerBackend
from .script import segment_script_runs

CAVEAT_PER_RUN_OVERSTATES_TOTAL = (
    "per-script-run token counts are each tokenizer run independently on "
    "that run's substring and summed; this can only overstate (never "
    "understate) the true whole-document token count, since it cannot "
    "find a merge spanning a run boundary -- use whole_document_tokens "
    "for actual cost, per_script_tokens for the breakdown story only"
)
CAVEAT_BASELINE_COMPARABLE_NOT_PARALLEL = (
    "any English baseline reported alongside this is comparable-genre "
    "(same kind of prose, independently sampled), not parallel "
    "(translated) text -- it controls for register, not matched "
    "information content"
)

# word_tokenize() alone (no BMWE compound merging) -- the "nopipe"-scheme
# granularity in burmesenlp.bench's terms. Stated explicitly per the same
# discipline bench uses: word count is scheme-dependent, and silently
# picking one without saying so makes the denominator unreproducible.
WORD_SCHEME = "nopipe (word_tokenize() alone, no BMWE compound merging)"


@dataclass(frozen=True)
class Denominators:
    bytes_: int
    chars: int
    syllables: int
    words: int
    word_scheme: str = WORD_SCHEME


@dataclass(frozen=True)
class ScriptTokenCount:
    script: str
    text: str
    tokens_per_tokenizer: Dict[str, int]


@dataclass(frozen=True)
class FertilityResult:
    text: str
    canonicalized: bool
    denominators: Denominators
    whole_document_tokens: Dict[str, int]
    per_script_runs: List[ScriptTokenCount]
    caveats: List[str] = field(
        default_factory=lambda: [CAVEAT_PER_RUN_OVERSTATES_TOTAL, CAVEAT_BASELINE_COMPARABLE_NOT_PARALLEL]
    )

    def ratios(self, tokenizer: str) -> Dict[str, Optional[float]]:
        """tokens-per-{byte,char,syllable,word} for one tokenizer, from
        whole_document_tokens. None where the denominator is zero."""
        n = self.whole_document_tokens[tokenizer]
        d = self.denominators
        return {
            "tokens_per_byte": n / d.bytes_ if d.bytes_ else None,
            "tokens_per_char": n / d.chars if d.chars else None,
            "tokens_per_syllable": n / d.syllables if d.syllables else None,
            "tokens_per_word": n / d.words if d.words else None,
        }


def _denominators(text: str) -> Denominators:
    from .. import syllable_tokenize, word_tokenize

    return Denominators(
        bytes_=len(text.encode("utf-8")),
        chars=len(text),
        syllables=len(syllable_tokenize(text)),
        words=len(word_tokenize(text)),
    )


def measure_text(
    text: str,
    backends: Dict[str, TokenizerBackend],
    *,
    canonicalize: bool = True,
) -> FertilityResult:
    """Measure fertility of *text* across the given tokenizer backends
    (name -> loaded backend, see :func:`burmesenlp.fertility.backends.load_backend`).

    Canonicalizes (canonical_order() + normalize()) by default -- required,
    not optional in practice: non-canonical mark order changes the byte
    sequence BPE actually sees, so measuring without it partly measures
    encoding-variant noise instead of tokenizer behavior. Disable only for
    a deliberate before/after comparison.

    Uses ``normalize()`` (strips zero-width space/joiner/BOM, then NFC),
    not a bare NFC call, and deliberately in that order (canonical_order()
    first): word_tokenize()/syllable_tokenize() both call normalize()
    internally before segmenting, so if this function used a different
    normalization the byte/char denominators would be measured against a
    different string than the one the word/syllable counts actually came
    from -- a real inconsistency caught while running this at corpus
    scale, not a hypothetical one (myPOS/Wikipedia text containing
    zero-width characters would have inflated char/byte counts relative
    to what the tokenizers saw).
    """
    if not isinstance(text, str):
        raise TypeError(f"expected str, got {type(text).__name__}")

    canon = _normalize_text(canonical_order(text)) if canonicalize else text
    denom = _denominators(canon)

    whole_doc = {name: len(backend.encode(canon)) for name, backend in backends.items()}

    runs = segment_script_runs(canon)
    per_script: List[ScriptTokenCount] = []
    for run in runs:
        counts = {name: len(backend.encode(run.text)) for name, backend in backends.items()}
        per_script.append(ScriptTokenCount(script=run.script, text=run.text, tokens_per_tokenizer=counts))

    return FertilityResult(
        text=canon,
        canonicalized=canonicalize,
        denominators=denom,
        whole_document_tokens=whole_doc,
        per_script_runs=per_script,
    )


def _percentile(sorted_values: Sequence[float], pct: float) -> float:
    if not sorted_values:
        return float("nan")
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * pct
    lo, hi = int(k), min(int(k) + 1, len(sorted_values) - 1)
    if lo == hi:
        return sorted_values[lo]
    frac = k - lo
    return sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac


def aggregate_distribution(results: Sequence[FertilityResult], tokenizer: str, ratio_key: str) -> Dict[str, object]:
    """Distribution (not just mean) of one ratio (e.g. "tokens_per_word")
    for one tokenizer across many FertilityResults.

    Reports percentiles/min/max/spread deliberately, the same discipline
    as F6's paragraph min/max/spread: a mean hides documents that are far
    worse than the average, and that's exactly the number a cost estimate
    needs.
    """
    values = sorted(
        v
        for r in results
        if (v := r.ratios(tokenizer).get(ratio_key)) is not None
    )
    if not values:
        return {
            "n": 0,
            "mean": None,
            "min": None,
            "p10": None,
            "p25": None,
            "median": None,
            "p75": None,
            "p90": None,
            "max": None,
            "spread": None,
        }
    return {
        "n": len(values),
        "mean": sum(values) / len(values),
        "min": values[0],
        "p10": _percentile(values, 0.10),
        "p25": _percentile(values, 0.25),
        "median": _percentile(values, 0.50),
        "p75": _percentile(values, 0.75),
        "p90": _percentile(values, 0.90),
        "max": values[-1],
        "spread": values[-1] - values[0],
    }


__all__ = [
    "Denominators",
    "ScriptTokenCount",
    "FertilityResult",
    "measure_text",
    "aggregate_distribution",
    "WORD_SCHEME",
    "CAVEAT_PER_RUN_OVERSTATES_TOTAL",
    "CAVEAT_BASELINE_COMPARABLE_NOT_PARALLEL",
]
