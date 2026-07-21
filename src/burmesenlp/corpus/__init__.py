"""Bundled linguistic resources for burmesenlp (not ML model weights).

Layout::

    corpus/
    ├── dictionaries/   words, stopwords, slang, ...
    ├── names/          person, locations, organizations, honorifics
    ├── syllables/      syllable lists and patterns
    ├── normalization/  unicode / zawgyi / punctuation rules
    ├── tokenizer/      vocabulary JSON only (BPE / EvoPiece)
    ├── pos/            tagset and lexicon JSON
    ├── ner/            gazetteers and labels
    ├── sentiment/      polarity and emotion lexicons
    ├── spell/          frequency, confusion, corrections
    └── metadata/       corpus.json registry snapshot

Model artifacts (CRF, embeddings binaries, SentencePiece .model, …) belong
under :mod:`burmesenlp.models`, not here.
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
