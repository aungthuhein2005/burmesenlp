"""High-level corpus export facade over pipeline ``Document`` objects."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, Iterable, List, Union

from ..pipeline.document import Document
from . import brat as brat_mod
from . import conll as conll_mod
from . import jsonl as jsonl_mod
from . import labelstudio as ls_mod
from .converter import document_to_sentences
from .schema import SentenceRecord

PathLike = Union[str, Path]


class CorpusExporter:
    """Convert ``Document`` analysis objects into training-friendly formats.

    The NLP pipeline and ``Document`` model are left unchanged; this layer
    only remaps existing annotations into non-redundant span records.
    """

    def to_records(self, doc: Document) -> List[SentenceRecord]:
        """Return sentence records for ``doc``."""
        return document_to_sentences(doc)

    def to_json(self, doc: Document) -> Dict[str, Any]:
        """Return ``{"sentences": [...]}`` without writing to disk."""
        return jsonl_mod.document_to_dict(self.to_records(doc))

    def to_jsonl(self, doc: Document) -> str:
        """Return newline-delimited JSON (one sentence object per line)."""
        return jsonl_mod.dumps_jsonl(self.to_records(doc))

    def to_conll(self, doc: Document) -> str:
        """Return CoNLL-style token rows for all sentences in ``doc``."""
        return conll_mod.dumps_conll(self.to_records(doc))

    def to_brat(self, doc: Document, *, basename: str = "document") -> Dict[str, str]:
        """Return ``{"txt": ..., "ann": ...}`` (``basename`` reserved for writers)."""
        _ = basename  # used by ``export_brat``; kept for API symmetry
        return brat_mod.dumps_brat(self.to_records(doc))

    def to_labelstudio(self, doc: Document) -> List[Dict[str, Any]]:
        """Return Label Studio task dicts (one per sentence)."""
        return ls_mod.to_labelstudio_tasks(self.to_records(doc))

    def export_jsonl(
        self,
        documents: Iterable[Document],
        path: PathLike,
        *,
        renumber: bool = True,
    ) -> None:
        """Write sentences from many documents to a ``.jsonl`` file.

        When ``renumber`` is true (default), sentence ``id`` values are
        reassigned globally ``0..N-1`` across the file for ML convenience.
        """
        sentences = self._iter_export_sentences(documents, renumber=renumber)
        jsonl_mod.dump_jsonl(sentences, path)

    def export_brat(
        self,
        doc: Document,
        out_dir: PathLike,
        *,
        basename: str = "document",
    ) -> None:
        """Write ``basename.txt`` and ``basename.ann`` under ``out_dir``."""
        brat_mod.write_brat(self.to_records(doc), out_dir, basename=basename)

    def _iter_export_sentences(
        self,
        documents: Iterable[Document],
        *,
        renumber: bool,
    ) -> List[SentenceRecord]:
        out: List[SentenceRecord] = []
        global_id = 0
        for doc in documents:
            for sentence in self.to_records(doc):
                if renumber:
                    out.append(replace(sentence, id=global_id))
                    global_id += 1
                else:
                    out.append(sentence)
        return out
