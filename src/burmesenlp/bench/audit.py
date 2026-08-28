"""BMWE-vs-gold compound disagreement audit.

Required before trusting any ``pipe``-scheme F1: burmesenlp's BMWE trie
and myPOS's ``|`` compound convention were built independently, by
different people, for different purposes. If they disagree about what
counts as a compound, boundary scoring reports that inventory mismatch
as segmentation error, not as the definitional difference it actually
is. This module finds disagreement spans; a human (or an agent standing
in for one) still has to look at each and judge which it is -- that
judgment is not automatable, so this only prepares the sample.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence

from .boundaries import canonical_reference_text, canonical_word_boundaries, word_boundaries

_MYANMAR_PUNCT = "၊။"  # ၊ ။


def _enclosing_gold_span(sorted_gold: List[int], text_len: int, pos: int) -> "tuple[int, int]":
    lo = max((b for b in sorted_gold if b <= pos), default=0)
    hi = min((b for b in sorted_gold if b >= pos), default=text_len)
    return lo, hi


def _spans_punctuation(text: str, start: int, end: int) -> bool:
    """True if the gold "one compound" span itself contains punctuation --
    a reliable tell that this isn't a lexical compound at all (e.g. a
    corpus artifact spanning across a sentence-final ။), not something
    any word/idiom-level merger should be expected to produce."""
    for ch in text[start:end]:
        if ch in _MYANMAR_PUNCT or unicodedata.category(ch).startswith("P"):
            return True
    return False


@dataclass
class Disagreement:
    text: str
    span_text: str
    direction: str  # "bmwe_merged_gold_split" or "bmwe_split_gold_merged"
    context_start: int
    context_end: int
    sentence_index: int
    crosses_punctuation: bool
    span_start: int  # enclosing gold "one compound" span, exact bounds
    span_end: int

    @property
    def compound_text(self) -> str:
        """The exact gold-merged span text (not the printed ±10-char context)."""
        return self.text[self.span_start : self.span_end]


def find_disagreements(
    gold_word_lists: Sequence[Sequence[str]],
    word_tokenize_fn: Callable[[str], List[str]],
    word_tokenize_plus_bmwe_fn: Callable[[str], List[str]],
) -> List[Disagreement]:
    """For each sentence, find spans where BMWE's merge decision disagrees
    with the compound-preserving (pipe-scheme) gold boundary set.

    A "merge decision" is any boundary present in plain word_tokenize()
    output but absent after BMWE runs -- i.e. BMWE joined two tokens.
    Disagreement means gold's boundary set doesn't match BMWE on that
    exact position.
    """
    out: List[Disagreement] = []
    for sentence_index, gold_words in enumerate(gold_word_lists):
        if not gold_words:
            continue
        text = canonical_reference_text(gold_words)
        gold_boundaries = canonical_word_boundaries(gold_words)
        sorted_gold = sorted(gold_boundaries)

        plain_words = word_tokenize_fn(text)
        plain_boundaries = word_boundaries(plain_words)
        bmwe_words = word_tokenize_plus_bmwe_fn(text)
        bmwe_boundaries = word_boundaries(bmwe_words)

        # positions BMWE removed (merged) relative to plain word_tokenize
        merged_by_bmwe = plain_boundaries - bmwe_boundaries
        for pos in merged_by_bmwe:
            if pos not in gold_boundaries:
                continue  # gold agrees it's a merge point too -- fine
            lo, hi = _enclosing_gold_span(sorted_gold, len(text), pos)
            out.append(
                Disagreement(
                    text=text,
                    span_text=text[max(0, pos - 10) : pos] + "|" + text[pos : pos + 10],
                    direction="bmwe_merged_gold_split",
                    context_start=max(0, pos - 10),
                    context_end=min(len(text), pos + 10),
                    sentence_index=sentence_index,
                    crosses_punctuation=_spans_punctuation(text, lo, hi),
                    span_start=lo,
                    span_end=hi,
                )
            )

        # positions gold merges (absent from gold_boundaries) but BMWE kept split
        for pos in plain_boundaries:
            if pos in bmwe_boundaries and pos not in gold_boundaries:
                # BMWE did NOT merge here (boundary survived), yet gold has
                # no boundary here either -- gold considers this one compound
                # that BMWE's trie missed entirely.
                lo, hi = _enclosing_gold_span(sorted_gold, len(text), pos)
                out.append(
                    Disagreement(
                        text=text,
                        span_text=text[max(0, pos - 10) : pos] + "|" + text[pos : pos + 10],
                        direction="bmwe_split_gold_merged",
                        context_start=max(0, pos - 10),
                        context_end=min(len(text), pos + 10),
                        sentence_index=sentence_index,
                        crosses_punctuation=_spans_punctuation(text, lo, hi),
                        span_start=lo,
                        span_end=hi,
                    )
                )
    return out


# Suffixes marking a productive grammatical derivation (verb/adjective ->
# noun), not a fixed lexical compound -- myPOS's "|" convention marks
# these liberally, but they're a regular grammar pattern (any verb can
# take -mhu/-yay), not idiom-trie material. Not exhaustive; a heuristic.
_DERIVATION_SUFFIXES = (
    "မှု",  # -hood / -ness / act-of (nominalizer)
    "ရေး",  # affairs-of / -ing (nominalizer)
    "ခြင်း",  # act-of (nominalizer)
    "စရာ",  # thing-to-V
    "နိုင်",  # can-V (modal)
    "ခွင့်",  # permission-to-V
)

_DIGITS = set("0123456789") | set("၀၁၂၃၄၅၆၇၈၉")


def categorize(d: Disagreement, is_proper_noun: Optional[Callable[[str], bool]] = None) -> str:
    """Bucket one disagreement span for --category: date_number /
    proper_noun / productive_derivation / genuine_compound (fallback --
    the actual candidates for growing BMWE's trie).

    Heuristic, not authoritative -- a starting point for triage, matching
    only what a human skim of the audit output would also flag. Order
    matters: punctuation-crossing/date checks are cheap and unambiguous,
    so they run before the costlier gazetteer-based proper-noun check.
    """
    span = d.compound_text
    if d.crosses_punctuation:
        return "date_number"  # crossing punctuation is almost always a decimal/date artifact
    if any(ch in _DIGITS for ch in span):
        return "date_number"
    if span.endswith(_DERIVATION_SUFFIXES):
        return "productive_derivation"
    if is_proper_noun is not None and is_proper_noun(span):
        return "proper_noun"
    return "genuine_compound"


def sample_diverse(disagreements: Sequence[Disagreement], n: int = 20) -> List[Disagreement]:
    """At most one disagreement per distinct sentence, spread across the
    full list rather than the first *n* raw positions -- a single long
    sentence can otherwise contribute most of a naive first-N sample
    (confirmed empirically: sequential sampling from this harness's own
    myPOS audit put >75% of a 20-item sample inside 4-5 sentences)."""
    seen_sentences = set()
    out: List[Disagreement] = []
    if not disagreements:
        return out
    step = max(1, len(disagreements) // (n * 20))
    for i in range(0, len(disagreements), step):
        d = disagreements[i]
        if d.sentence_index in seen_sentences:
            continue
        seen_sentences.add(d.sentence_index)
        out.append(d)
        if len(out) >= n:
            break
    return out
