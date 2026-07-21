"""Local cache for downloaded corpus resources."""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def cache_dir() -> Path:
    """Return (and create) the user cache directory for burmesenlp corpora."""
    override = os.environ.get("BURMESENLP_CACHE")
    if override:
        root = Path(override)
    else:
        root = Path.home() / ".cache" / "burmesenlp"
    root.mkdir(parents=True, exist_ok=True)
    return root


def clear_cache() -> None:
    """Delete all files under the corpus cache directory."""
    root = cache_dir()
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
