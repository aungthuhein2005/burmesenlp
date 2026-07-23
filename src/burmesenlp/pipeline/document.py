"""Pipeline document result (dict-compatible + JSON-serializable)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Tuple

from ..chunking.models import Chunk


@dataclass
class Document:
    """Full-pipeline output with attribute and mapping access.

    For ``json.dump``, use ``doc.to_dict()``::

        json.dump(doc.to_dict(), f, ensure_ascii=False, indent=4)
    """

    raw_text: str
    syllables: List[str]
    words: List[str]
    sentences: List[str]
    pos_tags: List[Tuple[str, str]]
    sentence_word_tags: List[List[Tuple[str, str]]]
    chunks: List[Chunk] = field(default_factory=list)

    _KEYS = (
        "raw_text",
        "syllables",
        "words",
        "sentences",
        "pos_tags",
        "sentence_word_tags",
        "chunks",
    )

    def __getitem__(self, key: str) -> Any:
        if not isinstance(key, str):
            raise TypeError(f"attribute name must be string, not {type(key).__name__!r}")
        try:
            return getattr(self, key)
        except AttributeError as exc:
            raise KeyError(key) from exc

    def __iter__(self) -> Iterator[str]:
        return iter(self._KEYS)

    def __len__(self) -> int:
        return len(self._KEYS)

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and key in self._KEYS

    def keys(self) -> Iterator[str]:
        return iter(self._KEYS)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Plain dict suitable for ``json.dump`` / ``json.dumps``."""
        return {
            "raw_text": self.raw_text,
            "syllables": list(self.syllables),
            "words": list(self.words),
            "sentences": list(self.sentences),
            "pos_tags": [list(pair) for pair in self.pos_tags],
            "sentence_word_tags": [
                [list(pair) for pair in sent] for sent in self.sentence_word_tags
            ],
            "chunks": [
                {
                    "type": c.type.value,
                    "text": c.text,
                    "tokens": list(c.tokens),
                    "pos_tags": list(c.pos_tags),
                    "start": c.start,
                    "end": c.end,
                    "features": dict(c.features),
                }
                for c in self.chunks
            ],
        }

    def to_json(self, *, ensure_ascii: bool = False, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=ensure_ascii, indent=indent)
