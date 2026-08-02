"""Corpus export layer: convert ``Document`` analysis objects to ML formats.

This package is independent of the parser implementation. Use
``CorpusExporter`` to emit JSON / JSONL / CoNLL / BRAT / Label Studio
payloads without modifying the pipeline or ``Document`` model.
"""

from __future__ import annotations

from .exporter import CorpusExporter
from .importer import CorpusImporter
from .schema import (
    ChunkRecord,
    ClauseRecord,
    EntityRecord,
    MWERecord,
    SentenceRecord,
    TokenRecord,
)

__all__ = [
    "ChunkRecord",
    "ClauseRecord",
    "CorpusExporter",
    "CorpusImporter",
    "EntityRecord",
    "MWERecord",
    "SentenceRecord",
    "TokenRecord",
]
