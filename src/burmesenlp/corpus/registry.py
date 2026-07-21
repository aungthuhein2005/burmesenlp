"""Registry of available corpus resources (bundled + downloadable)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

_CORPUS_ROOT = Path(__file__).parent

# Relative paths that ship inside the package.  Downloadable extras can be
# registered later via metadata/corpus.json "resources" entries.
_BUNDLED: Dict[str, Dict[str, str]] = {
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
    "dictionaries/slang": {
        "path": "dictionaries/slang.txt",
        "kind": "txt",
        "description": "Slang / informal terms",
    },
    "dictionaries/abbreviations": {
        "path": "dictionaries/abbreviations.txt",
        "kind": "txt",
        "description": "Abbreviations",
    },
    "dictionaries/foreign_words": {
        "path": "dictionaries/foreign_words.txt",
        "kind": "txt",
        "description": "Foreign / loan words",
    },
    "dictionaries/emoji": {
        "path": "dictionaries/emoji.txt",
        "kind": "txt",
        "description": "Emoji lexicon",
    },
    "names/person": {
        "path": "names/person.txt",
        "kind": "txt",
        "description": "Person names",
    },
    "names/locations": {
        "path": "names/locations.txt",
        "kind": "txt",
        "description": "Location names",
    },
    "names/organizations": {
        "path": "names/organizations.txt",
        "kind": "txt",
        "description": "Organization names",
    },
    "names/honorifics": {
        "path": "names/honorifics.txt",
        "kind": "txt",
        "description": "Honorifics",
    },
    "syllables/syllables": {
        "path": "syllables/syllables.txt",
        "kind": "txt",
        "description": "Syllable inventory",
    },
    "syllables/patterns": {
        "path": "syllables/patterns.json",
        "kind": "json",
        "description": "Syllable patterns",
    },
    "normalization/unicode_rules": {
        "path": "normalization/unicode_rules.json",
        "kind": "json",
        "description": "Unicode normalization rules",
    },
    "normalization/zawgyi_mapping": {
        "path": "normalization/zawgyi_mapping.json",
        "kind": "json",
        "description": "Zawgyi mapping tables",
    },
    "normalization/punctuation": {
        "path": "normalization/punctuation.json",
        "kind": "json",
        "description": "Punctuation normalization",
    },
    "tokenizer/bpe_vocab": {
        "path": "tokenizer/bpe_vocab.json",
        "kind": "json",
        "description": "BPE vocabulary (linguistic resource; models live under burmesenlp.models)",
    },
    "tokenizer/evopiece_vocab": {
        "path": "tokenizer/evopiece_vocab.json",
        "kind": "json",
        "description": "EvoPiece vocabulary (linguistic resource; models live under burmesenlp.models)",
    },
    "pos/tagset": {
        "path": "pos/tagset.json",
        "kind": "json",
        "description": "POS tagset",
    },
    "pos/lexicon": {
        "path": "pos/lexicon.json",
        "kind": "json",
        "description": "POS lexicon",
    },
    "ner/gazetteer_person": {
        "path": "ner/gazetteer_person.txt",
        "kind": "txt",
        "description": "NER person gazetteer",
    },
    "ner/gazetteer_location": {
        "path": "ner/gazetteer_location.txt",
        "kind": "txt",
        "description": "NER location gazetteer",
    },
    "ner/gazetteer_org": {
        "path": "ner/gazetteer_org.txt",
        "kind": "txt",
        "description": "NER organization gazetteer",
    },
    "ner/labels": {
        "path": "ner/labels.json",
        "kind": "json",
        "description": "NER label set",
    },
    "sentiment/positive": {
        "path": "sentiment/positive.txt",
        "kind": "txt",
        "description": "Positive sentiment lexicon",
    },
    "sentiment/negative": {
        "path": "sentiment/negative.txt",
        "kind": "txt",
        "description": "Negative sentiment lexicon",
    },
    "sentiment/emotion": {
        "path": "sentiment/emotion.json",
        "kind": "json",
        "description": "Emotion lexicon",
    },
    "spell/frequency": {
        "path": "spell/frequency.json",
        "kind": "json",
        "description": "Word frequency table",
    },
    "spell/confusion": {
        "path": "spell/confusion.json",
        "kind": "json",
        "description": "Confusion sets",
    },
    "spell/corrections": {
        "path": "spell/corrections.json",
        "kind": "json",
        "description": "Spelling corrections",
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
