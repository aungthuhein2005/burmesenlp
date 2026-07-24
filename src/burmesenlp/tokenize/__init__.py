"""Tokenization package: syllable, word, and sentence segmentation.

Architecture
------------
Call sites use engine-dispatched helpers (``word_tokenize(engine=...)``).
v1 provides only the rule-based ``longest`` word engine; v2+ statistical
and neural tokenizers register in :mod:`burmesenlp.tokenize.engine` without
reorganizing this package.
"""

from __future__ import annotations

from typing import List, Optional

from ..lexicon import Lexicon
from ..normalize import normalize
from .engine import available_word_engines, get_word_engine, register_word_engine
from .longest import WordSegmenter
from .sentence import Sentence, SentenceSegmenter
from .syllable import (
    ANUSVARA,
    ASAT,
    DIGITS,
    FULL_STOP,
    MEDIALS,
    MY_DIGITS,
    OTHER,
    PUNCT,
    SECTION,
    STACK_VIRAMA,
    SYLLABLE,
    TONES,
    VOWEL_SIGNS,
    Token,
    syllable_segment,
    syllable_tokenize,
    tokenize,
)
from .word import word_tokenize, word_tokens


def sentence_tokenize(
    text: str,
    *,
    lexicon: Optional[Lexicon] = None,
    split_on_final_particles: bool = True,
    engine: str = "longest",
) -> List[str]:
    """Segment *text* into sentences via the grammar-aware pipeline.

    Runs word tokenization (*engine*), BMWE, POS, and phrase chunking,
    then splits on chunk/POS structure (not bare သည်/တယ် matching).
    """
    del engine  # word engine selection is owned by BurmeseNLP / longest today
    from ..pipeline import BurmeseNLP

    return BurmeseNLP(
        lexicon=lexicon,
        split_on_final_particles=split_on_final_particles,
    ).sentence_segment(text)


__all__ = [
    "ANUSVARA",
    "ASAT",
    "DIGITS",
    "FULL_STOP",
    "MEDIALS",
    "MY_DIGITS",
    "OTHER",
    "PUNCT",
    "SECTION",
    "STACK_VIRAMA",
    "SYLLABLE",
    "TONES",
    "Token",
    "VOWEL_SIGNS",
    "Sentence",
    "SentenceSegmenter",
    "WordSegmenter",
    "available_word_engines",
    "get_word_engine",
    "register_word_engine",
    "sentence_tokenize",
    "syllable_segment",
    "syllable_tokenize",
    "tokenize",
    "word_tokenize",
    "word_tokens",
]
