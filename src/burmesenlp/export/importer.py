"""Corpus import foundation (JSON / JSONL today; CoNLL stubbed)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Union

from . import jsonl as jsonl_mod
from .schema import SentenceRecord

PathLike = Union[str, Path]


class CorpusImporter:
    """Load span-based sentence records from serialized corpora.

    Does **not** reconstruct pipeline ``Document`` objects — only the
    export schema.
    """

    @staticmethod
    def from_json(data: Union[str, Dict[str, Any], Path]) -> List[SentenceRecord]:
        """Load from a document dict, JSON string, or ``.json`` path."""
        return jsonl_mod.load_json(data)

    @staticmethod
    def from_jsonl(source: Union[str, Path]) -> List[SentenceRecord]:
        """Load from a ``.jsonl`` path or a JSONL string."""
        return jsonl_mod.load_jsonl(source)

    @staticmethod
    def from_conll(source: Union[str, Path]) -> List[SentenceRecord]:
        """Reserved for future CoNLL import."""
        raise NotImplementedError(
            "CorpusImporter.from_conll is not implemented yet; "
            "use from_json / from_jsonl for round-trips"
        )
