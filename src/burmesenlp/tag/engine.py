"""POS-tagger engine registry.

v1 ships only ``\"rule\"``.  Future backends (CRF, Transformer) register
here so ``pos_tag(..., engine=...)`` stays stable across versions.
"""

from __future__ import annotations

from typing import Callable, Dict, List

from ..lexicon import Lexicon
from .rule import POSTagger

TaggerFactory = Callable[[Lexicon], POSTagger]


def _xlmr_factory(lexicon: Lexicon) -> POSTagger:
    """Lazily import :mod:`burmesenlp.tag.xlmr` (optional ``transformers``/``torch``)."""
    from .xlmr import XLMRTagger

    return XLMRTagger(lexicon)  # type: ignore[return-value]


_TAG_ENGINES: Dict[str, TaggerFactory] = {
    "rule": POSTagger,
    "xlmr": _xlmr_factory,
}


def available_tag_engines() -> List[str]:
    return sorted(_TAG_ENGINES)


def get_tag_engine(name: str) -> TaggerFactory:
    try:
        return _TAG_ENGINES[name]
    except KeyError as exc:
        raise ValueError(
            f"unknown POS tag engine {name!r}; "
            f"available: {available_tag_engines()}"
        ) from exc


def register_tag_engine(name: str, factory: TaggerFactory) -> None:
    """Register a future POS tagging backend (v2+)."""
    _TAG_ENGINES[name] = factory
