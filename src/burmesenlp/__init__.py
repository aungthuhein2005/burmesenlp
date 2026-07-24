"""Myanmar (Burmese) NLP preprocessing toolkit.

Public API (stable surface — use these from application code):
    BurmeseNLP / process / Document -- full pipeline facade
    Lexicon / LexiconError / POS_TAGS
    BMWEEngine / MWEEntry / MWEToken
    normalize / looks_like_zawgyi
    uni2zg / zg2uni / to_unicode / is_zawgyi
    word_tokenize / syllable_tokenize / sentence_tokenize / pos_tag
    chunk / chunk_from_tokens / Chunk / ChunkType
    syllable_segment / Token
"""

from .chunking import Chunk, ChunkType, chunk, chunk_from_tokens
from .lexicon import POS_TAGS, Lexicon, LexiconError
from .mwe import BMWEEngine, MWEEntry, MWEToken
from .normalize import looks_like_zawgyi, normalize
from .pipeline import BurmeseNLP, process
from .pipeline.document import Document
from .tag import pos_tag
from .tokenize import sentence_tokenize, syllable_tokenize, word_tokenize
from .tokenize.syllable import Token, syllable_segment
from .zawgyi import is_zawgyi, to_unicode, uni2zg, zg2uni

__version__ = "1.0.0"

__all__ = [
    "BurmeseNLP",
    "Document",
    "process",
    "Lexicon",
    "LexiconError",
    "POS_TAGS",
    "BMWEEngine",
    "MWEEntry",
    "MWEToken",
    "normalize",
    "looks_like_zawgyi",
    "is_zawgyi",
    "to_unicode",
    "uni2zg",
    "zg2uni",
    "word_tokenize",
    "syllable_tokenize",
    "sentence_tokenize",
    "pos_tag",
    "chunk",
    "chunk_from_tokens",
    "Chunk",
    "ChunkType",
    "syllable_segment",
    "Token",
    "__version__",
]
