"""Frozen vocabulary snapshots for ``--freeze-strata``.

OOV is defined relative to the lexicon. Expanding the lexicon moves
tokens from OOV to in-vocabulary, so a naive before/after comparison of
the OOV stratum is scoring a *different token set* each time -- that
measures set composition, not accuracy. A snapshot freezes which tokens
count as OOV so both runs score the same stratum membership; only the
segmenter's own behavior on those (frozen) OOV tokens is free to change.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import FrozenSet

from ..lexicon import Lexicon
from ..normalize import canonical_order, normalize


def snapshot_vocabulary(lexicon: Lexicon) -> FrozenSet[str]:
    """Canonicalized word-form set of *lexicon*, for freezing or comparing."""
    return frozenset(canonical_order(normalize(w, warn_zawgyi=False)) for w in lexicon._entries)


def save_snapshot(path: Path, vocab: FrozenSet[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(vocab), ensure_ascii=False, indent=0), encoding="utf-8")


def load_snapshot(path: Path) -> FrozenSet[str]:
    return frozenset(json.loads(path.read_text(encoding="utf-8")))


def load_or_create_snapshot(path: Path, lexicon: Lexicon) -> "tuple[FrozenSet[str], bool]":
    """Load the frozen snapshot at *path*, creating it from *lexicon*'s
    current vocabulary if it doesn't exist yet. Returns (vocab, created).

    Call this before making a single change to the lexicon -- the first
    invocation for a given path is what defines "pre-expansion."
    """
    if path.exists():
        return load_snapshot(path), False
    vocab = snapshot_vocabulary(lexicon)
    save_snapshot(path, vocab)
    return vocab, True
