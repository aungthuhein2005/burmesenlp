"""Local cache for downloaded gold corpora (never vendored into the wheel).

Distinct from :mod:`burmesenlp.models.cache` -- that cache holds model
*weights*; this one holds evaluation *corpora*, several of which carry
NonCommercial licenses (see :mod:`burmesenlp.bench` for why that matters).
Kept in a separate directory so clearing one never touches the other.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def corpus_cache_dir() -> Path:
    """Return (and create) the user cache directory for gold corpora."""
    override = os.environ.get("BURMESENLP_CORPUS_CACHE")
    if override:
        root = Path(override)
    else:
        root = Path.home() / ".cache" / "burmesenlp" / "corpora"
    root.mkdir(parents=True, exist_ok=True)
    return root


def clear_corpus_cache() -> None:
    """Delete all files under the corpus cache directory."""
    root = corpus_cache_dir()
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
