"""High-level facade combining normalization, tokenization and tagging.

Public entry points:
    BurmeseNLP  -- stateful pipeline (lexicon, options)
    process     -- one-shot ``BurmeseNLP(...).process(text)``
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from ..chunking import PhraseChunker
from ..chunking.models import Chunk
from ..lexicon import Lexicon
from ..normalize import normalize
from ..tag.rule import POSTagger
from ..tokenize.longest import WordSegmenter
from ..tokenize.sentence import Sentence, SentenceSegmenter
from ..tokenize.syllable import (
    ANUSVARA,
    ASAT,
    FULL_STOP,
    MEDIALS,
    MY_DIGITS,
    SECTION,
    STACK_VIRAMA,
    TONES,
    VOWEL_SIGNS,
    Token,
    tokenize,
)
from .document import Document


class BurmeseNLP:
    """Myanmar (Burmese) NLP preprocessing pipeline.

    All character positions returned by this class refer to the
    *normalized* form of the input (zero-width characters stripped, NFC
    applied); ``normalize()`` is exposed so callers can reproduce it.

    Loading a dictionary that does not exist or is malformed raises
    ``LexiconError`` instead of silently falling back.  Custom files
    (``.json`` or ``.txt``) are merged on top of the bundled default
    lexicon with per-word tag union; pass ``lexicon=...`` for full control.
    """

    def __init__(
        self,
        dictionary_path: Optional[str] = None,
        *,
        lexicon: Optional[Lexicon] = None,
        split_on_final_particles: bool = True,
    ):
        if lexicon is not None:
            self.lexicon = lexicon
        elif dictionary_path is not None:
            self.lexicon = Lexicon.from_file(dictionary_path, merge_default=True)
        else:
            self.lexicon = Lexicon.default()

        self._segmenter = WordSegmenter(self.lexicon)
        self._sentencer = SentenceSegmenter(
            split_on_final_particles=split_on_final_particles
        )
        self._tagger = POSTagger(self.lexicon)
        self._chunker = PhraseChunker()

    # ------------------------------------------------------------------
    # Internal helpers (operate on already-normalized text)
    # ------------------------------------------------------------------

    def _word_tokens(self, norm: str) -> List[Token]:
        return self._segmenter.segment(tokenize(norm))

    def _sentences(self, norm: str) -> List[Sentence]:
        return self._sentencer.segment(self._word_tokens(norm), norm)

    # ------------------------------------------------------------------
    # Segmentation
    # ------------------------------------------------------------------

    def syllable_segment(self, text: str) -> List[str]:
        """Segment text into syllables (foundation for all other steps)."""
        return [t.text for t in tokenize(normalize(text))]

    def syllable_tokens(self, text: str) -> List[Token]:
        """Syllable tokens with offsets into the normalized text."""
        return tokenize(normalize(text))

    def word_segment(self, text: str) -> List[str]:
        """Segment text into words."""
        return [t.text for t in self._word_tokens(normalize(text))]

    def word_tokens(self, text: str) -> List[Token]:
        """Word tokens with offsets into the normalized text."""
        return self._word_tokens(normalize(text))

    def sentence_segment(self, text: str) -> List[str]:
        """Segment text into sentences."""
        norm = normalize(text)
        return [s.text for s in self._sentences(norm)]

    def sentence_segment_with_positions(self, text: str) -> List[Tuple[str, int, int]]:
        """Sentences with (start, end) offsets into the *normalized* text.

        Guaranteed: ``normalize(text)[start:end] == sentence``.
        """
        norm = normalize(text)
        return [(s.text, s.start, s.end) for s in self._sentences(norm)]

    # ------------------------------------------------------------------
    # POS tagging
    # ------------------------------------------------------------------

    def pos_tag(self, words: Sequence[str]) -> List[Tuple[str, str]]:
        """Tag an already-segmented word list."""
        return self._tagger.tag(words)

    # ------------------------------------------------------------------
    # Phrase chunking
    # ------------------------------------------------------------------

    def chunk_from_tokens(
        self,
        words: Sequence[str],
        pos_tags: Sequence[object],
    ) -> List[Chunk]:
        """Chunk from words + POS tags (does not re-tag)."""
        return self._chunker.chunk(words, pos_tags)

    def chunk(self, text: str) -> List[Chunk]:
        """Segment, POS-tag, then chunk *text*."""
        words = self.word_segment(text)
        return self.chunk_from_tokens(words, self.pos_tag(words))

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def process(self, text: str) -> Document:
        """Run the full pipeline once, with all outputs mutually consistent.

        Flow: normalize → syllable tokenize → word tokenize → sentence
        split → POS tag → phrase chunk.  Words are segmented a single time
        and shared by the sentence splitter, tagger, and chunker.
        """
        norm = normalize(text)
        syllable_tokens = tokenize(norm)
        word_tokens = self._segmenter.segment(syllable_tokens)
        words = [t.text for t in word_tokens]
        sentences = self._sentencer.segment(word_tokens, norm)
        pos_tags = self._tagger.tag(words)
        chunks = self._chunker.chunk(words, pos_tags)

        sentence_word_tags: List[List[Tuple[str, str]]] = []
        idx = 0
        for sent in sentences:
            count = len(sent.words)
            sentence_word_tags.append(pos_tags[idx : idx + count])
            idx += count

        return Document(
            raw_text=norm,
            syllables=[t.text for t in syllable_tokens],
            words=words,
            sentences=[s.text for s in sentences],
            pos_tags=pos_tags,
            sentence_word_tags=sentence_word_tags,
            chunks=chunks,
        )

    # ------------------------------------------------------------------
    # Dictionary management
    # ------------------------------------------------------------------

    def add_to_dictionary(self, word: str, tags: Iterable[str]) -> None:
        """Add a word with POS tags (validated; raises LexiconError)."""
        self.lexicon.add(word, tags)

    def save_dictionary(self, path: str) -> None:
        """Atomically save the current dictionary as UTF-8 JSON."""
        self.lexicon.save(path)

    # ------------------------------------------------------------------
    # Statistics & feature extraction
    # ------------------------------------------------------------------

    def get_stats(self, text: str) -> Dict:
        """Basic statistics about the text."""
        result = self.process(text)
        dist: Dict[str, int] = defaultdict(int)
        for _, tag in result["pos_tags"]:
            dist[tag] += 1
        return {
            "char_count": len(result["raw_text"]),
            "syllable_count": len(result["syllables"]),
            "word_count": len(result["words"]),
            "sentence_count": len(result["sentences"]),
            "avg_words_per_sentence": (
                len(result["words"]) / max(len(result["sentences"]), 1)
            ),
            "avg_syllables_per_word": (
                len(result["syllables"]) / max(len(result["words"]), 1)
            ),
            "pos_distribution": dict(dist),
        }

    def extract_features_for_crf(self, text: str) -> List[Dict]:
        """Per-syllable feature dicts for training CRF / BiLSTM-CRF models."""
        tokens = tokenize(normalize(text))
        features: List[Dict] = []

        for i, tok in enumerate(tokens):
            syl = tok.text
            feat: Dict = {
                "syllable": syl,
                "len": len(syl),
                "first_char": syl[0],
                "last_char": syl[-1],
                "has_medial": any(c in MEDIALS for c in syl),
                "has_vowel_sign": any(c in VOWEL_SIGNS for c in syl),
                "has_tone": any(c in TONES for c in syl),
                "has_asat": ASAT in syl,
                "has_anusvara": ANUSVARA in syl,
                "has_stacked": STACK_VIRAMA in syl,
                "is_digit": all(c in MY_DIGITS for c in syl),
                "is_punctuation": syl in (SECTION, FULL_STOP),
            }

            if i > 0:
                feat["prev_syllable"] = tokens[i - 1].text
                feat["prev_len"] = len(tokens[i - 1].text)
            else:
                feat["BOS"] = True

            if i < len(tokens) - 1:
                feat["next_syllable"] = tokens[i + 1].text
                feat["next_len"] = len(tokens[i + 1].text)
            else:
                feat["EOS"] = True

            if len(syl) >= 2:
                feat["bigram_0_1"] = syl[:2]
                feat["bigram_-2_-1"] = syl[-2:]
            if len(syl) >= 3:
                feat["trigram_0_2"] = syl[:3]

            features.append(feat)

        return features


def process(text: str, **kwargs) -> Document:
    """One-shot pipeline: normalize → tokenize → sentences → POS → chunks."""
    return BurmeseNLP(**kwargs).process(text)
