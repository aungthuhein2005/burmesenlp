"""Boundary-level evaluation harness for burmesenlp word segmentation.

burmesenlp has never been scored against a gold corpus before this
module existed. Published Burmese segmentation numbers (90-94%, ~80%)
are not directly usable as targets: none of them states the word
scheme they were measured against, and myPOS and ALT disagree with each
other about what counts as one Burmese word. Every score this module
produces states its corpus, scheme, and n in the output header for
exactly that reason -- never read an aggregate F1 from here without
those three.

Licensing -- read before extending this module
------------------------------------------------
Every gold corpus wired in here is CC BY-NC-SA (NonCommercial) or
stricter (myPOS v3.0: verified via its README, not assumed; ALT
Treebank: CC BY-NC-SA per its own documentation). Corpora are fetched
to a local cache directory at runtime and are NEVER vendored into this
repository or the burmesenlp wheel (Apache-2.0).

This has a consequence beyond the corpus files themselves: any
*derived* artifact -- n-gram counts, frequency tables, trained model
weights, cached statistics -- computed from a CC BY-NC-SA corpus is
plausibly a derivative work under that license, and so is plausibly
NOT shippable inside the Apache-2.0 burmesenlp package either. This
module and its callers must not persist myPOS- or ALT-derived data
anywhere that ends up in a release artifact. If you are building a
feature (e.g. a lattice segmenter) that wants n-gram statistics derived
from one of these corpora, that data has to live outside the wheel
(regenerated locally by whoever needs it, or shipped from a separately
licensed source) -- flag the question rather than building the
persistence path.

Boundary counts (not token counts)
-----------------------------------
Every score here is boundary-level precision/recall/F1 over sets of
character offsets, not token accuracy -- see :mod:`burmesenlp.bench.boundaries`
for why. Both hypothesis and gold are canonicalized with
:func:`burmesenlp.normalize.canonical_order` before scoring, since Myanmar
combining marks are almost all Canonical_Combining_Class 0 and NFC
cannot reorder them -- without this step, encoding variance (measured at
1.183% type-level / 4.518% token-occurrence on myPOS) would be scored as
segmentation error.
"""

from __future__ import annotations

from .boundaries import BoundaryCounts, score_corpus, score_corpus_stratified
from .corpora import ALT_LICENSE, MYPOS_LICENSE, GoldSentence, collapse_stats, load_alt, load_mypos
from .freeze import load_or_create_snapshot, load_snapshot, save_snapshot, snapshot_vocabulary
from .holdout import read_log as read_alt_holdout_log
from .holdout import record_run as record_alt_run

__all__ = [
    "ALT_LICENSE",
    "BoundaryCounts",
    "GoldSentence",
    "MYPOS_LICENSE",
    "collapse_stats",
    "load_alt",
    "load_mypos",
    "load_or_create_snapshot",
    "load_snapshot",
    "read_alt_holdout_log",
    "record_alt_run",
    "save_snapshot",
    "score_corpus",
    "score_corpus_stratified",
    "snapshot_vocabulary",
]
