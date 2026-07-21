"""Load registered model artifacts (stub in v1)."""

from __future__ import annotations

from typing import Any

from .registry import model_info


class ModelError(RuntimeError):
    """Raised when a model cannot be loaded."""


def load_model(name: str) -> Any:
    """Load a named model.

    v1 ships no model weights.  Calling this raises :class:`ModelError`
    until a backend is registered and marked available.
    """
    info = model_info(name)
    if info is None:
        raise ModelError(
            f"unknown model {name!r}; planned names: "
            f"crf, fasttext, transformer, sentencepiece, evopiece"
        )
    if not info.get("available"):
        raise ModelError(
            f"model {name!r} is reserved for a future release "
            f"({info.get('description', 'n/a')}); burmesenlp v1 is rule-based only"
        )
    raise ModelError(f"model {name!r} is marked available but has no loader yet")
