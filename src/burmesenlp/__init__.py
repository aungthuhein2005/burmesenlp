"""Myanmar (Burmese) NLP preprocessing toolkit.

Public API (stable surface — use these from application code):
    BurmeseNLP / process / Document -- full pipeline facade
    Lexicon / LexiconError / POS_TAGS
    BMWEEngine / MWEEntry / MWEToken
    GazetteerManager / EntityType / GazetteerHit
    CorpusExporter / CorpusImporter -- span-based corpus export
    normalize / looks_like_zawgyi / canonical_order
    uni2zg / zg2uni / to_unicode / is_zawgyi
    get_zawgyi_probability / convert_with_report -- calibrated Zawgyi
        detection and auditable conversion with a per-rule repair log
    word_tokenize / syllable_tokenize / sentence_tokenize / pos_tag
    chunk / chunk_from_tokens / Chunk / ChunkType
    syllable_segment / Token
"""

from .chunking import (
    Chunk,
    ChunkType,
    Clause,
    ClauseParser,
    ClauseType,
    Phrase,
    SyntaxSentence,
    chunk,
    chunk_from_tokens,
)
from .export import CorpusExporter, CorpusImporter
from .gazetteer import EntityType, GazetteerHit, GazetteerManager
from .lexicon import POS_TAGS, Lexicon, LexiconError
from .mwe import BMWEEngine, MWEEntry, MWEToken
from .normalize import canonical_order, looks_like_zawgyi, normalize
from .pipeline import BurmeseNLP, process
from .pipeline.document import Document
from .tag import pos_tag
from .tokenize import sentence_tokenize, syllable_tokenize, word_tokenize
from .tokenize.syllable import Token, syllable_segment
from .zawgyi import (
    ZawgyiReport,
    convert_with_report,
    get_zawgyi_probability,
    is_zawgyi,
    to_unicode,
    uni2zg,
    zg2uni,
)

__version__ = "1.1.0"

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
    "GazetteerManager",
    "GazetteerHit",
    "EntityType",
    "CorpusExporter",
    "CorpusImporter",
    "normalize",
    "looks_like_zawgyi",
    "canonical_order",
    "is_zawgyi",
    "to_unicode",
    "uni2zg",
    "zg2uni",
    "get_zawgyi_probability",
    "convert_with_report",
    "ZawgyiReport",
    "word_tokenize",
    "syllable_tokenize",
    "sentence_tokenize",
    "pos_tag",
    "chunk",
    "chunk_from_tokens",
    "Chunk",
    "ChunkType",
    "Clause",
    "ClauseParser",
    "ClauseType",
    "Phrase",
    "SyntaxSentence",
    "syllable_segment",
    "Token",
    "__version__",
]
