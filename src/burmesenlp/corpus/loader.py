"""Load bundled corpus resources from the package tree."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Union

from .registry import corpus_root, resource_info


class CorpusError(FileNotFoundError):
    """Raised when a corpus resource cannot be resolved or read."""


def resource_path(name_or_relpath: str) -> Path:
    """Resolve a registry name or relative path under the corpus root.

    Examples::

        resource_path("dictionaries/words")
        resource_path("dictionaries/words.txt")
    """
    info = resource_info(name_or_relpath)
    if info is not None and "path" in info:
        path = corpus_root() / info["path"]
    else:
        path = corpus_root() / name_or_relpath
    if not path.is_file():
        raise CorpusError(f"corpus resource not found: {name_or_relpath!r} ({path})")
    return path


def load_lines(
    name_or_relpath: str,
    *,
    skip_empty: bool = True,
    skip_comments: bool = True,
) -> List[str]:
    """Load a text resource as a list of lines (UTF-8)."""
    path = resource_path(name_or_relpath)
    lines: List[str] = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if skip_empty and not line:
            continue
        if skip_comments and line.startswith("#"):
            continue
        lines.append(line)
    return lines


def load_json(name_or_relpath: str) -> Union[Dict[str, Any], List[Any]]:
    """Load a JSON corpus resource."""
    path = resource_path(name_or_relpath)
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise CorpusError(f"invalid JSON in {path}: {exc}") from exc
