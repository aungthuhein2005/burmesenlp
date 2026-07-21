"""Myanmar (Burmese) NLP preprocessing toolkit.

Public API (stable surface — use these from application code):
    BurmeseNLP / process -- full pipeline facade
    Lexicon / LexiconError / POS_TAGS
    normalize / looks_like_zawgyi
    uni2zg / zg2uni / to_unicode / is_zawgyi
    word_tokenize / syllable_tokenize / sentence_tokenize / pos_tag
    syllable_segment / Token
"""

from .lexicon import POS_TAGS, Lexicon, LexiconError
from .normalize import looks_like_zawgyi, normalize
from .pipeline import BurmeseNLP, process
from .tag import pos_tag
from .tokenize import sentence_tokenize, syllable_tokenize, word_tokenize
from .tokenize.syllable import Token, syllable_segment
from .zawgyi import is_zawgyi, to_unicode, uni2zg, zg2uni

__version__ = "1.0.0"

__all__ = [
    "BurmeseNLP",
    "process",
    "Lexicon",
    "LexiconError",
    "POS_TAGS",
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
    "syllable_segment",
    "Token",
    "__version__",
]
