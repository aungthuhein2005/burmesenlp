"""Local cache for downloaded model artifacts (distinct from corpus cache)."""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def model_cache_dir() -> Path:
    """Return (and create) the user cache directory for burmesenlp models."""
    override = os.environ.get("BURMESENLP_MODEL_CACHE")
    if override:
        root = Path(override)
    else:
        root = Path.home() / ".cache" / "burmesenlp" / "models"
    root.mkdir(parents=True, exist_ok=True)
    return root


def clear_model_cache() -> None:
    """Delete all files under the model cache directory."""
    root = model_cache_dir()
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
