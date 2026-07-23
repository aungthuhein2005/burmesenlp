"""Greedy priority-based phrase chunker (exceptions → phrases → clauses)."""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple, Union

from ..lexicon import Lexicon
from ..normalize import normalize
from ..tag.rule import POSTagger
from ..tokenize.longest import WordSegmenter
from ..tokenize.syllable import tokenize
from .models import Chunk, ChunkType, make_chunk, normalize_pos_input
from .rules import CompiledGrammar, default_grammar

PosInput = Union[Sequence[str], Sequence[Tuple[str, str]]]


class PhraseChunker:
    """Shallow phrase chunker: consumes words + POS, never mutates tags."""

    def __init__(self, grammar: Optional[CompiledGrammar] = None):
        self._grammar = grammar if grammar is not None else default_grammar()

    def chunk(
        self,
        words: Sequence[str],
        pos_tags: PosInput,
    ) -> List[Chunk]:
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

        # 1. Exceptions / fixed expressions (highest precedence)
        chunks.extend(self._match_exceptions(words, tags, covered))

        # 2. Phrase patterns by priority (skip CLAUSE — handled via markers)
        chunks.extend(self._match_phrases(words, tags, covered))

        # 3. Clause spans from boundary markers (may overlay phrases)
        chunks.extend(self._split_clauses(words, tags))

        chunks.sort(key=lambda c: (c.start, c.end, c.type.value))
        return chunks

    def _match_exceptions(
        self,
        words: List[str],
        tags: List[str],
        covered: List[bool],
    ) -> List[Chunk]:
        exc = self._grammar.exceptions
        # Longer texts first so "မင်္ဂလာပါ" wins over shorter prefixes
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
        """If words[start:] joins to *text*, return exclusive end index."""
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
                if rule.type == ChunkType.CLAUSE:
                    continue  # clauses come from markers
                end = compiled.match_at(words, tags, i)
                if end is None or end <= i:
                    continue
                if any(covered[j] for j in range(i, end)):
                    continue
                key = (rule.priority, end - i)
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

    def _split_clauses(
        self,
        words: List[str],
        tags: List[str],
    ) -> List[Chunk]:
        markers = self._grammar.markers.all_clause_markers()
        if not markers:
            return []
        marker_set = set(markers)

        boundaries = [0]
        for i, w in enumerate(words):
            if w in marker_set:
                cut = i + 1  # attach marker to the left clause
                if cut > boundaries[-1] and cut < len(words):
                    boundaries.append(cut)
        boundaries.append(len(words))

        chunks: List[Chunk] = []
        for a, b in zip(boundaries, boundaries[1:]):
            if b <= a:
                continue
            if all(tags[j] == "PUNCT" for j in range(a, b)):
                continue
            chunks.append(make_chunk(ChunkType.CLAUSE, words, tags, a, b - 1))
        if len(chunks) <= 1 and not any(w in marker_set for w in words):
            return []
        return chunks


def chunk_from_tokens(
    words: Sequence[str],
    pos_tags: PosInput,
    *,
    grammar: Optional[CompiledGrammar] = None,
) -> List[Chunk]:
    return PhraseChunker(grammar).chunk(words, pos_tags)


def chunk(
    text: str,
    *,
    lexicon: Optional[Lexicon] = None,
    grammar: Optional[CompiledGrammar] = None,
) -> List[Chunk]:
    """Normalize → segment → POS tag → chunk."""
    lex = lexicon if lexicon is not None else Lexicon.default()
    norm = normalize(text)
    words = [t.text for t in WordSegmenter(lex).segment(tokenize(norm))]
    tags = POSTagger(lex).tag(words)
    return chunk_from_tokens(words, tags, grammar=grammar)
