"""Greedy priority-based phrase chunker (exceptions → entities → phrases).

Gazetteer entity spans (PERSON / TOWN / …) are locked as NP *before*
POS-pattern matching so names are not split across NP/PP incorrectly.

Clause structure is built by :class:`ClauseParser` from these phrase
chunks — never by scanning words alone.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple, Union

from ..gazetteer.models import GazetteerHit
from ..lexicon import Lexicon
from ..normalize import normalize
from ..tag.rule import POSTagger
from ..tokenize.longest import WordSegmenter
from ..tokenize.syllable import tokenize
from .models import Chunk, ChunkType, is_clause_type, make_chunk, normalize_pos_input
from .rules import CompiledGrammar, default_grammar

PosInput = Union[Sequence[str], Sequence[Tuple[str, str]]]
SentenceBound = Tuple[int, int]


class PhraseChunker:
    """Shallow phrase chunker: consumes words + POS, never mutates tags."""

    def __init__(self, grammar: Optional[CompiledGrammar] = None):
        self._grammar = grammar if grammar is not None else default_grammar()

    def chunk(
        self,
        words: Sequence[str],
        pos_tags: PosInput,
        *,
        entities: Optional[Sequence[GazetteerHit]] = None,
        clauses: bool = False,
        sentence_bounds: Optional[Sequence[SentenceBound]] = None,
    ) -> List[Chunk]:
        """Chunk phrases, optionally locking gazetteer entity spans as NP.

        Parameters
        ----------
        entities:
            Post-BMWE gazetteer hits. Each span is emitted as one ``NP`` with
            ``features["entity"]`` set, and is blocked from further POS
            pattern matching.
        """
        del clauses, sentence_bounds  # API compat; clauses live in ClauseParser
        words = list(words)
        tags = normalize_pos_input(pos_tags)
        if len(words) != len(tags):
            raise ValueError(
                f"words/pos_tags length mismatch: {len(words)} != {len(tags)}"
            )
        if not words:
            return []

        covered = [False] * len(words)
        chunks: List[Chunk] = []
        # 1. Fixed expressions / greetings
        chunks.extend(self._match_exceptions(words, tags, covered))
        # 2. Gazetteer entities → locked NP (semantic → syntactic bridge)
        chunks.extend(self._lock_entities(words, tags, covered, entities or ()))
        # 3. POS phrase patterns on remaining tokens
        chunks.extend(self._match_phrases(words, tags, covered))
        chunks.sort(key=lambda c: (c.start, c.end, c.type.value))
        return chunks

    def split_clauses(
        self,
        words: Sequence[str],
        pos_tags: PosInput,
        *,
        sentence_bounds: Optional[Sequence[SentenceBound]] = None,
    ) -> List[Chunk]:
        """Deprecated: clause overlays removed from the phrase chunker.

        Returns ``[]``. Prefer :class:`ClauseParser`.
        """
        del words, pos_tags, sentence_bounds
        return []

    def _lock_entities(
        self,
        words: List[str],
        tags: List[str],
        covered: List[bool],
        entities: Sequence[GazetteerHit],
    ) -> List[Chunk]:
        """Force one NP per non-overlapping gazetteer span.

        Longer spans first so multi-token PERSON names win over fragments.
        """
        chunks: List[Chunk] = []
        ordered = sorted(
            entities,
            key=lambda e: (e.start, -(e.end - e.start + 1)),
        )
        for ent in ordered:
            start, end = ent.start, ent.end
            if start < 0 or end >= len(words) or end < start:
                continue
            if any(covered[j] for j in range(start, end + 1)):
                continue
            for j in range(start, end + 1):
                covered[j] = True
            # Entity spans are proper nouns for downstream syntax — do not keep
            # garbage per-token tags (PRON/VERB/…) from name syllables.
            locked_tags = list(tags)
            for j in range(start, end + 1):
                locked_tags[j] = "PROPN"
            features = {
                "entity": ent.entity_type.value,
                **{
                    str(k): str(v)
                    for k, v in ent.attributes.items()
                    if v is not None
                },
            }
            chunks.append(
                make_chunk(
                    ChunkType.NOUN_PHRASE,
                    words,
                    locked_tags,
                    start,
                    end,
                    features=features,
                )
            )
        return chunks

    def _match_exceptions(
        self,
        words: List[str],
        tags: List[str],
        covered: List[bool],
    ) -> List[Chunk]:
        exc = self._grammar.exceptions
        catalog: List[Tuple[str, ChunkType]] = list(exc.special_phrases) + list(
            exc.fixed_expressions
        )
        catalog.sort(key=lambda x: len(x[0]), reverse=True)

        chunks: List[Chunk] = []
        n = len(words)
        i = 0
        while i < n:
            if covered[i]:
                i += 1
                continue
            matched = False
            for text, ctype in catalog:
                end = self._match_joined_text(words, i, text)
                if end is None:
                    continue
                if any(covered[j] for j in range(i, end)):
                    continue
                for j in range(i, end):
                    covered[j] = True
                chunks.append(make_chunk(ctype, words, tags, i, end - 1))
                i = end
                matched = True
                break
            if not matched:
                i += 1
        return chunks

    @staticmethod
    def _match_joined_text(
        words: List[str],
        start: int,
        text: str,
    ) -> Optional[int]:
        acc = ""
        for j in range(start, len(words)):
            acc += words[j]
            if acc == text:
                return j + 1
            if not text.startswith(acc):
                return None
        return None

    def _match_phrases(
        self,
        words: List[str],
        tags: List[str],
        covered: List[bool],
    ) -> List[Chunk]:
        n = len(words)
        chunks: List[Chunk] = []
        i = 0
        while i < n:
            if covered[i]:
                i += 1
                continue
            best: Optional[Tuple[int, int, ChunkType, object]] = None
            best_key: Optional[Tuple[int, int]] = None
            for rule, compiled in self._grammar.pattern_rules:
                if is_clause_type(rule.type):
                    continue
                end = compiled.match_at(words, tags, i)
                if end is None or end <= i:
                    continue
                if any(covered[j] for j in range(i, end)):
                    continue
                # Maximal munch: longer span wins; priority only breaks ties.
                # Idioms / greetings use _match_exceptions (explicit path).
                key = (end - i, rule.priority)
                if best_key is None or key > best_key:
                    best_key = key
                    best = (i, end, rule.type, rule.features)
            if best is None:
                i += 1
                continue
            start, end, ctype, features = best
            for j in range(start, end):
                covered[j] = True
            chunks.append(
                make_chunk(ctype, words, tags, start, end - 1, features=features)
            )
            i = end
        return chunks


def chunk_from_tokens(
    words: Sequence[str],
    pos_tags: PosInput,
    *,
    grammar: Optional[CompiledGrammar] = None,
    entities: Optional[Sequence[GazetteerHit]] = None,
    clauses: bool = False,
    sentence_bounds: Optional[Sequence[SentenceBound]] = None,
) -> List[Chunk]:
    return PhraseChunker(grammar).chunk(
        words,
        pos_tags,
        entities=entities,
        clauses=clauses,
        sentence_bounds=sentence_bounds,
    )


def chunk(
    text: str,
    *,
    lexicon: Optional[Lexicon] = None,
    grammar: Optional[CompiledGrammar] = None,
    gazetteer: Optional[object] = None,
    use_gazetteer: bool = True,
) -> List[Chunk]:
    """Normalize → segment → POS → optional gazetteer → phrase chunk.

    When ``use_gazetteer`` is True (default), entity spans are locked as NP
    the same way as ``BurmeseNLP.process``. Pass ``use_gazetteer=False`` for
    a fast syntax-only pass, or inject a preloaded ``GazetteerManager``.
    """
    from ..gazetteer.manager import GazetteerManager

    lex = lexicon if lexicon is not None else Lexicon.default()
    norm = normalize(text)
    words = [t.text for t in WordSegmenter(lex).segment(tokenize(norm))]
    tags = POSTagger(lex).tag(words)
    entities: List[GazetteerHit] = []
    if use_gazetteer or gazetteer is not None:
        gaz = gazetteer if gazetteer is not None else GazetteerManager(lexicon=lex)
        entities = list(gaz.find_all(words))
    return chunk_from_tokens(words, tags, grammar=grammar, entities=entities)
