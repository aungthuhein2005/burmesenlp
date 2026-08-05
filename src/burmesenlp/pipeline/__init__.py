"""High-level facade combining normalization, tokenization and tagging.

Public entry points:
    BurmeseNLP  -- stateful pipeline (lexicon, options)
    process     -- one-shot ``BurmeseNLP(...).process(text)``
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from ..chunking import PhraseChunker
from ..chunking.chunker import PosInput
from ..chunking.clause import ClauseParser
from ..chunking.models import Chunk
from ..gazetteer import GazetteerManager
from ..gazetteer.models import GazetteerHit
from ..lexicon import Lexicon
from ..mwe import BMWEEngine
from ..mwe.models import MWEToken
from ..normalize import normalize
from ..tag.rule import POSTagger
from ..tokenize.longest import WordSegmenter
from ..tokenize.sentence import SentenceSegmenter, merged_char_spans
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

    Zawgyi is **not** auto-converted: call ``zg2uni`` / ``to_unicode`` before
    ``process`` when the encoding is Zawgyi or unknown.

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
        gazetteer: bool = True,
        gazetteer_manager: Optional[GazetteerManager] = None,
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
        self._mwe = BMWEEngine(lexicon=self.lexicon)
        self._tagger = POSTagger(self.lexicon)
        self._chunker = PhraseChunker()
        self._clause_parser = ClauseParser()
        self._gazetteer: Optional[GazetteerManager] = None
        # Gazetteer NER after POS on post-BMWE words → Document.entities
        if gazetteer_manager is not None:
            self._gazetteer_enabled = True
            self._gazetteer = gazetteer_manager
        else:
            self._gazetteer_enabled = gazetteer
            self._gazetteer = None

    def _get_gazetteer(self) -> Optional[GazetteerManager]:
        if not self._gazetteer_enabled:
            return None
        if self._gazetteer is None:
            self._gazetteer = GazetteerManager(lexicon=self.lexicon, autoload=True)
        return self._gazetteer

    # ------------------------------------------------------------------
    # Internal helpers (operate on already-normalized text)
    # ------------------------------------------------------------------

    def _word_tokens(self, norm: str) -> List[Token]:
        return self._segmenter.segment(tokenize(norm))

    def _analyze(self, norm: str):
        """Shared path: words → BMWE → POS → gazetteer → phrases → sentences → clauses.

        Gazetteer NER runs on post-BMWE ``words``; entity spans are then
        locked as NP inside the phrase chunker (``doc.entities`` stays the
        semantic layer; ``doc.chunks`` gains entity-backed NPs).
        """
        word_tokens = self._segmenter.segment(tokenize(norm))
        pre_mwe = [t.text for t in word_tokens]
        words, mwe_spans = self._mwe.process_detailed(pre_mwe)
        pos_tags = self._tagger.tag(words, mwe=mwe_spans)
        gaz = self._get_gazetteer()
        entities: List[GazetteerHit] = (
            gaz.find_all(words, pos_tags=[t for _, t in pos_tags])
            if gaz is not None
            else []
        )
        phrase_chunks = self._chunker.chunk(words, pos_tags, entities=entities)
        char_spans = merged_char_spans(word_tokens, mwe_spans)
        sentences = self._sentencer.segment_from_chunks(
            words, pos_tags, phrase_chunks, norm, char_spans=char_spans
        )
        sentence_bounds = [(s.word_start, s.word_end) for s in sentences]
        syntax = self._clause_parser.parse_sentences(
            phrase_chunks,
            sentence_bounds=sentence_bounds,
            sentence_texts=[s.text for s in sentences],
            sentence_char_spans=[(s.start, s.end) for s in sentences],
            words=words,
        )
        return (
            word_tokens,
            words,
            mwe_spans,
            pos_tags,
            phrase_chunks,
            sentences,
            syntax,
            entities,
        )

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
        """Segment text into sentences (grammar-aware: POS + chunks)."""
        norm = normalize(text)
        if not norm:
            return []
        *_, sentences, _syntax, _entities = self._analyze(norm)
        return [s.text for s in sentences]

    def sentence_segment_with_positions(self, text: str) -> List[Tuple[str, int, int]]:
        """Sentences with (start, end) offsets into the *normalized* text.

        Guaranteed: ``normalize(text)[start:end] == sentence``.
        """
        norm = normalize(text)
        if not norm:
            return []
        *_, sentences, _syntax, _entities = self._analyze(norm)
        return [(s.text, s.start, s.end) for s in sentences]
    # ------------------------------------------------------------------
    # POS tagging
    # ------------------------------------------------------------------

    def pos_tag(
        self,
        words: Sequence[str],
        *,
        mwe: Optional[Sequence[MWEToken]] = None,
    ) -> List[Tuple[str, str]]:
        """Tag an already-segmented word list (optionally MWE-aware)."""
        return self._tagger.tag(words, mwe=mwe)

    # ------------------------------------------------------------------
    # Phrase chunking
    # ------------------------------------------------------------------

    def chunk_from_tokens(
        self,
        words: Sequence[str],
        pos_tags: PosInput,
    ) -> List[Chunk]:
        """Chunk from words + POS tags (does not re-tag)."""
        return self._chunker.chunk(words, pos_tags)

    def chunk(self, text: str) -> List[Chunk]:
        """Segment, MWE-merge, POS-tag, then chunk *text*."""
        pre = self.word_segment(text)
        words, mwe_spans = self._mwe.process_detailed(pre)
        return self.chunk_from_tokens(words, self.pos_tag(words, mwe=mwe_spans))

    def load_mwe(
        self,
        path: str,
        *,
        category: Optional[str] = None,
        priority: int = 0,
    ) -> int:
        """Load an additional MWE resource (JSON/TXT) into the engine."""
        return self._mwe.load(path, category=category, priority=priority)

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def process(self, text: str) -> Document:
        """Run the full pipeline once, with all outputs mutually consistent.

        Flow: normalize → syllables → words → BMWE → POS → gazetteer NER
        → phrase chunk (entity spans locked as NP) → sentences → ClauseParser.

        ``doc.entities`` is the semantic gazetteer layer; matching spans also
        appear as NP chunks with ``features["entity"]``. Pass ``gazetteer=False``
        to skip NER.
        """
        norm = normalize(text)
        syllable_tokens = tokenize(norm)
        if not norm:
            return Document(
                raw_text=norm,
                syllables=[],
                words=[],
                sentences=[],
                pos_tags=[],
                sentence_word_tags=[],
                chunks=[],
                mwe=[],
                entities=[],
                sentence_trees=[],
            )

        (
            _word_tokens,
            words,
            mwe_spans,
            pos_tags,
            chunks,
            sentences,
            syntax,
            entities,
        ) = self._analyze(norm)

        sentence_word_tags: List[List[Tuple[str, str]]] = [
            pos_tags[s.word_start : s.word_end] for s in sentences
        ]

        return Document(
            raw_text=norm,
            syllables=[t.text for t in syllable_tokens],
            words=words,
            sentences=[s.text for s in sentences],
            pos_tags=pos_tags,
            sentence_word_tags=sentence_word_tags,
            chunks=chunks,
            mwe=mwe_spans,
            entities=entities,
            sentence_trees=list(syntax),
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
    """One-shot pipeline: normalize → words → MWE → POS → gazetteer → phrases → sentences → clauses.

    Does not auto-convert Zawgyi; use ``zg2uni`` / ``to_unicode`` first if needed.
    """
    return BurmeseNLP(**kwargs).process(text)
