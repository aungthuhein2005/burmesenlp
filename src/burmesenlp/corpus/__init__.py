"""Bundled resource registry for burmesenlp (not used by the V1 pipeline).

Holds the general word list, stopwords, gazetteer lookup lists, idioms,
and phrase-chunking grammar, addressable by name via
:func:`resource_path`/:func:`load_lines`/:func:`load_json`.

The empty placeholder trees reserved here for later hybrid/ML versions
(``ner/``, ``sentiment/``, ``spell/``, ``embeddings/``, ``tokenizer/``,
``names/``, ``syllables/``, ``pos/``, ``normalization/``) were removed --
they shipped no content and nothing referenced them; see
:mod:`burmesenlp.models` for the equivalent forward-looking registry
pattern done right (a ``_PLANNED`` dict with no on-disk footprint).

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
