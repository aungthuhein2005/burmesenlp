"""Boundary-level P/R/F1: score sets of split-point offsets, not tokens.

Token accuracy hides the actual failure mode -- one wrong boundary
corrupts two adjacent tokens and distorts a token-level number. Scoring
the *set* of boundary offsets directly avoids that: a single missed or
spurious split costs exactly one boundary, not two tokens.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Sequence, Set

from ..normalize import canonical_order, normalize


def word_boundaries(words: Sequence[str]) -> Set[int]:
    """Boundary offsets between consecutive words (never 0 or the total
    length -- those are string edges, not splits)."""
    boundaries = set()
    cum = 0
    for w in words[:-1]:
        cum += len(w)
        boundaries.add(cum)
    return boundaries


def canonical_reference_text(words: Sequence[str]) -> str:
    """Concatenate *words* (normalized + canonicalized per-word) into the
    exact string both gold and hypothesis boundaries are measured against.

    Per-word normalization/canonicalization is equivalent to doing it on
    the joined string, since NFC composition and canonical_order() never
    act across a word boundary for Myanmar text -- and per-word keeps
    gold boundary offsets trivial to compute (cumulative word lengths),
    with no separate position-remapping step needed. Both canonical_order()
    and normalize() only reorder/delete zero-width marks *within* one
    syllable cluster or strip standalone zero-width characters; neither
    inserts characters, so this is safe.
    """
    return "".join(canonical_order(normalize(w, warn_zawgyi=False)) for w in words)


def canonical_word_boundaries(words: Sequence[str]) -> Set[int]:
    canon_words = [canonical_order(normalize(w, warn_zawgyi=False)) for w in words]
    return word_boundaries(canon_words)


@dataclass
class BoundaryCounts:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    def add(self, hyp: Set[int], gold: Set[int]) -> None:
        self.tp += len(hyp & gold)
        self.fp += len(hyp - gold)
        self.fn += len(gold - hyp)

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0


def score_corpus(
    gold_word_lists: Sequence[Sequence[str]],
    segment_fn,
) -> "tuple[BoundaryCounts, List[dict]]":
    """Micro-averaged boundary P/R/F1 over every gold sentence.

    *segment_fn* receives the canonicalized reference text for one
    sentence and must return the hypothesis word list for that same text
    (so hypothesis and gold boundaries are computed over identical
    characters -- no offset remapping needed).

    Returns (aggregate counts, per-sentence detail list) -- the detail
    list is what --diff and the BMWE disagreement audit consume.
    """
    counts = BoundaryCounts()
    detail = []
    for gold_words in gold_word_lists:
        if len(gold_words) < 1:
            continue
        reference_text = canonical_reference_text(gold_words)
        gold_boundaries = canonical_word_boundaries(gold_words)
        hyp_words = segment_fn(reference_text)
        hyp_boundaries = word_boundaries(hyp_words)
        counts.add(hyp_boundaries, gold_boundaries)
        detail.append(
            {
                "text": reference_text,
                "gold_words": gold_words,
                "hyp_words": hyp_words,
                "gold_boundaries": gold_boundaries,
                "hyp_boundaries": hyp_boundaries,
            }
        )
    return counts, detail


def _position_strata(canon_words: Sequence[str], is_in_lexicon: Callable[[str], bool]) -> Dict[int, bool]:
    """Map every non-edge character position in the joined text to
    "is IV" (True) / "is OOV" (False).

    A position on the junction between two gold words is IV only if
    *both* neighboring words are in-lexicon (an OOV word's boundary is
    an OOV-generalization test either way it's approached). A position
    strictly inside one gold word (never a real gold boundary, only ever
    reachable by a spurious hypothesis split) inherits that one word's
    IV/OOV status.
    """
    strata: Dict[int, bool] = {}
    cum = 0
    word_iv = [is_in_lexicon(w) for w in canon_words]
    for i, w in enumerate(canon_words):
        start = cum
        end = cum + len(w)
        for p in range(start + 1, end):
            strata[p] = word_iv[i]
        cum = end
        if i < len(canon_words) - 1:
            strata[end] = word_iv[i] and word_iv[i + 1]
    return strata


@dataclass
class StratifiedCounts:
    iv: BoundaryCounts
    oov: BoundaryCounts


def score_corpus_stratified(
    gold_word_lists: Sequence[Sequence[str]],
    segment_fn,
    is_in_lexicon: Callable[[str], bool],
) -> StratifiedCounts:
    """Boundary P/R/F1 split by whether the surrounding gold word(s) are
    in the segmenter's own lexicon.

    Answers a different question than plain :func:`score_corpus`: not
    "how good is the segmentation overall" but "how much of that number
    is memorized vocabulary vs. genuine generalization to unseen words."
    A boundary position is OOV-stratum if it touches an out-of-lexicon
    gold word at all -- see :func:`_position_strata`.
    """
    result = StratifiedCounts(iv=BoundaryCounts(), oov=BoundaryCounts())
    for gold_words in gold_word_lists:
        if len(gold_words) < 1:
            continue
        canon_words = [canonical_order(normalize(w, warn_zawgyi=False)) for w in gold_words]
        reference_text = "".join(canon_words)
        gold_boundaries = word_boundaries(canon_words)
        hyp_words = segment_fn(reference_text)
        hyp_boundaries = word_boundaries(hyp_words)

        strata = _position_strata(canon_words, is_in_lexicon)

        gold_iv = {p for p in gold_boundaries if strata.get(p, True)}
        gold_oov = gold_boundaries - gold_iv
        hyp_iv = {p for p in hyp_boundaries if strata.get(p, True)}
        hyp_oov = hyp_boundaries - hyp_iv

        result.iv.add(hyp_iv, gold_iv)
        result.oov.add(hyp_oov, gold_oov)
    return result
