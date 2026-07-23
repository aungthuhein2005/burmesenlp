"""POS tagging package (engine-dispatched).

Architecture
------------
v1 ``engine=\"rule\"``::

    words → candidate POS → context rules → grammar rules → final POS

Rules *filter* candidates (do not blindly assign).  See
:mod:`burmesenlp.tag.rules` and :mod:`burmesenlp.tag.disambiguator`.
v2+: CRF / hybrid; v3: Transformer — register in :mod:`burmesenlp.tag.engine`.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from ..lexicon import Lexicon
from .engine import available_tag_engines, get_tag_engine, register_tag_engine
from .rule import POSTagger


def pos_tag(
    words: Sequence[str],
    engine: str = "rule",
    *,
    lexicon: Optional[Lexicon] = None,
) -> List[Tuple[str, str]]:
    """Tag an already-segmented word list."""
    lex = lexicon if lexicon is not None else Lexicon.default()
    tagger = get_tag_engine(engine)(lex)
    return tagger.tag(words)


__all__ = [
    "POSTagger",
    "available_tag_engines",
    "get_tag_engine",
    "pos_tag",
    "register_tag_engine",
]
