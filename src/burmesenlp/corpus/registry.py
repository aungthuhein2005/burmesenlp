"""Registry of available corpus resources (bundled + downloadable)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

_CORPUS_ROOT = Path(__file__).parent

# Relative paths that ship inside the package.  Downloadable extras can be
# registered later via metadata/corpus.json "resources" entries.
_BUNDLED: Dict[str, Dict[str, Any]] = {
    "dictionaries/words": {
        "path": "dictionaries/words.txt",
        "kind": "txt",
        "description": "General word list",
    },
    "dictionaries/stopwords": {
        "path": "dictionaries/stopwords.txt",
        "kind": "txt",
        "description": "Stopwords",
    },
    "metadata/corpus": {
        "path": "metadata/corpus.json",
        "kind": "json",
        "description": "Corpus metadata",
    },
}


def _metadata_resources() -> Dict[str, Dict[str, Any]]:
    meta_path = _CORPUS_ROOT / "metadata" / "corpus.json"
    if not meta_path.is_file():
        return {}
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    extras: Dict[str, Dict[str, Any]] = {}
    for entry in data.get("resources", []) or []:
        name = entry.get("name")
        if isinstance(name, str) and name:
            extras[name] = entry
    return extras


def list_resources() -> List[str]:
    """Return sorted names of all registered corpus resources."""
    names = set(_BUNDLED) | set(_metadata_resources())
    return sorted(names)


def resource_info(name: str) -> Optional[Dict[str, Any]]:
    """Return metadata for *name*, or ``None`` if unknown."""
    if name in _BUNDLED:
        info = dict(_BUNDLED[name])
        info["name"] = name
        info["bundled"] = True
        return info
    extras = _metadata_resources()
    if name in extras:
        info = dict(extras[name])
        info["name"] = name
        info.setdefault("bundled", False)
        return info
    return None


def corpus_root() -> Path:
    """Filesystem root of the bundled corpus package data."""
    return _CORPUS_ROOT
