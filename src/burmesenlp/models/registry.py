"""Registry of named model backends (empty in v1)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Reserved names for the roadmap; no artifacts are shipped in v1.
_PLANNED: Dict[str, Dict[str, Any]] = {
    "crf": {"description": "CRF sequence tagger (v2)", "available": False},
    "fasttext": {"description": "fastText embeddings (v2)", "available": False},
    "transformer": {"description": "Transformer models (v3)", "available": False},
    "sentencepiece": {"description": "SentencePiece tokenizer model (v2+)", "available": False},
    "evopiece": {"description": "EvoPiece tokenizer (v4)", "available": False},
}

_MODELS: Dict[str, Dict[str, Any]] = dict(_PLANNED)


def available_models(*, include_planned: bool = False) -> List[str]:
    """Return registered model names (empty unless *include_planned*)."""
    if include_planned:
        return sorted(_MODELS)
    return sorted(n for n, info in _MODELS.items() if info.get("available"))


def model_info(name: str) -> Optional[Dict[str, Any]]:
    info = _MODELS.get(name)
    if info is None:
        return None
    out = dict(info)
    out["name"] = name
    return out


def register_model(name: str, info: Dict[str, Any]) -> None:
    """Register a model entry (used when v2+ artifacts are added)."""
    _MODELS[name] = dict(info)
