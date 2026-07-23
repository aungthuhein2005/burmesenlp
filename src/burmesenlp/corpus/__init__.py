"""Bundled resource scaffold for burmesenlp (not used by the V1 pipeline).

Layout is reserved for later hybrid / ML versions.  Empty or stub trees
(``ner/``, ``sentiment/``, ``spell/``, ``embeddings/``, ``tokenizer/``, …)
are placeholders — not public V1 features.

Production V1 linguistic data lives under ``burmesenlp.lexicon`` and
``burmesenlp.zawgyi``.  See ``corpus/README.md`` for details.
"""

from __future__ import annotations

from .cache import cache_dir, clear_cache
from .downloader import download
from .loader import load_json, load_lines, resource_path
from .registry import list_resources, resource_info

__all__ = [
    "cache_dir",
    "clear_cache",
    "download",
    "list_resources",
    "load_json",
    "load_lines",
    "resource_info",
    "resource_path",
]
