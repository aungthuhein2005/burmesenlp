"""Phrase-based clause parser (YAML-driven).

Linguistic pipeline placement
-----------------------------
    words + POS → phrase chunks → **ClauseParser** → SyntaxSentence tree

Rules of thumb (V1)
-------------------
1. Operate on phrase chunks, never on bare word streams alone.
2. Combine phrase patterns **and** grammar markers (``clause_rules.yml``).
3. Relative constructions nest inside NP (RelativeModifier + HeadNoun) —
   they are **not** top-level Sentence clauses.
4. Purpose: NP…VP+marker → PURPOSE clause; bare VP+marker → Purpose VP.
5. PP semantic roles come from ``semantic_roles.yml`` (default only).
6. MAIN requires final VP + end marker *inside* that VP + template match
   (:func:`is_valid_main_clause`) — never a bare သည် / ပြီ / ပါ alone.
7. Phrase templates are an explicit V1 list; matching is swappable via
   :class:`~burmesenlp.chunking.pattern_match.PhrasePatternMatcher` (TODO V2 grammar).
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from .models import (
    ROLE_HEAD_NOUN,
    ROLE_RELATIVE_MODIFIER,
    TOP_LEVEL_CLAUSE_TYPES,
    Chunk,
    ChunkType,
    Clause,
    ClauseRules,
    ClauseType,
    Phrase,
    PostpositionRoles,
    SyntaxSentence,
    chunk_to_phrase,
    is_clause_type,
)
from .pattern_match import PhrasePatternMatcher, default_pattern_matcher
from .rules import CompiledGrammar, default_grammar

SentenceBound = Tuple[int, int]

# Phrase-type labels used in YAML phrase_patterns
_TYPE_LABEL = {
    ChunkType.NOUN_PHRASE: "NP",
    ChunkType.VERB_PHRASE: "VP",
    ChunkType.POSTPOSITIONAL_PHRASE: "PP",
    ChunkType.ADJECTIVE_PHRASE: "ADJP",
    ChunkType.NUMERAL_PHRASE: "NUMP",
    ChunkType.GREETING: "GREETING",
    ChunkType.FIXED_EXPRESSION: "FIXED_EXPRESSION",
    ChunkType.FIXED_VERB: "FIXED_VERB",
}

_VP_LIKE = frozenset(
    {
        ChunkType.VERB_PHRASE,
        ChunkType.FIXED_VERB,
        ChunkType.GREETING,
    }
)


class ClauseParser:
    """Build Sentence → Clause → Phrase trees from phrase chunks."""

    def __init__(
        self,
        grammar: Optional[CompiledGrammar] = None,
        *,
        pattern_matcher: Optional[PhrasePatternMatcher] = None,
    ):
        self._grammar = grammar if grammar is not None else default_grammar()
        # V1: ExplicitListMatcher. Swap for a grammar engine in V2 without
        # changing parse_window / parse_sentences signatures.
        self._pattern_matcher = pattern_matcher or default_pattern_matcher()

    @property
    def clause_rules(self) -> ClauseRules:
        return self._grammar.clause_rules

    @property
    def postposition_roles(self) -> PostpositionRoles:
        return self._grammar.postposition_roles

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse_sentences(
        self,
        phrase_chunks: Sequence[Chunk],
        *,
        sentence_bounds: Sequence[SentenceBound],
        sentence_texts: Optional[Sequence[str]] = None,
        sentence_char_spans: Optional[Sequence[Tuple[int, int]]] = None,
        words: Optional[Sequence[str]] = None,
    ) -> List[SyntaxSentence]:
        """Parse one ``SyntaxSentence`` per ``(word_start, word_end)`` bound."""
        phrases = self._chunks_to_phrases(phrase_chunks)
        word_list = list(words) if words is not None else []
        out: List[SyntaxSentence] = []
        for i, (ws, we) in enumerate(sentence_bounds):
            text = ""
            cs = ce = 0
            if sentence_texts is not None and i < len(sentence_texts):
                text = sentence_texts[i]
            if sentence_char_spans is not None and i < len(sentence_char_spans):
                cs, ce = sentence_char_spans[i]
            window = [p for p in phrases if p.start < we and p.end >= ws]
            window = sorted(window, key=lambda p: (p.start, p.end))
            nested, clauses = self._parse_window(window, words=word_list)
            out.append(
                SyntaxSentence(
                    text=text or "".join(p.text for p in nested),
                    start=cs,
                    end=ce,
                    word_start=ws,
                    word_end=we,
                    clauses=tuple(clauses),
                    phrases=tuple(nested),
                )
            )
        return out

    def parse_window(
        self,
        phrase_chunks: Sequence[Chunk],
        *,
        words: Optional[Sequence[str]] = None,
    ) -> SyntaxSentence:
        """Parse a single window (e.g. one punct-bounded sentence)."""
        phrases = self._chunks_to_phrases(phrase_chunks)
        nested, clauses = self._parse_window(phrases, words=list(words or []))
        if not phrases:
            return SyntaxSentence("", 0, 0, 0, 0, (), ())
        return SyntaxSentence(
            text="".join(p.text for p in nested),
            start=0,
            end=0,
            word_start=phrases[0].start,
            word_end=phrases[-1].end + 1,
            clauses=tuple(clauses),
            phrases=tuple(nested),
        )

    # ------------------------------------------------------------------
    # Phrase enrichment (syntax ≠ semantics)
    # ------------------------------------------------------------------

    def _chunks_to_phrases(self, chunks: Sequence[Chunk]) -> List[Phrase]:
        out: List[Phrase] = []
        for ch in chunks:
            if is_clause_type(ch.type):
                continue  # ignore legacy clause overlays
            gram = None
            sem = None
            if ch.type == ChunkType.POSTPOSITIONAL_PHRASE:
                gram, sem = self._pp_roles(ch)
            elif ch.type in _VP_LIKE:
                gram = "PREDICATE"
            out.append(
                chunk_to_phrase(
                    ch, grammatical_function=gram, semantic_role=sem
                )
            )
        return sorted(out, key=lambda p: (p.start, p.end))

    def _pp_roles(self, chunk: Chunk) -> Tuple[Optional[str], Optional[str]]:
        """Assign grammatical_function + default semantic_role from YAML."""
        if not chunk.tokens:
            return "ADJUNCT", None
        postp = chunk.tokens[-1]
        info = self.postposition_roles.get(postp)
        if info is None:
            return "ADJUNCT", None
        return info.grammatical_function, info.default_role

    # ------------------------------------------------------------------
    # Window parse: relatives → marked clauses → MAIN
    # ------------------------------------------------------------------

    def _parse_window(
        self,
        phrases: List[Phrase],
        *,
        words: Optional[Sequence[str]] = None,
    ) -> Tuple[List[Phrase], List[Clause]]:
        if not phrases:
            return [], []
        word_list = list(words or [])
        phrases = self._split_internal_markers(phrases)
        if self.clause_rules.settings.allow_nested_relative:
            nested = self._nest_relatives(phrases, words=word_list)
        else:
            nested = list(phrases)
        clauses = self._cut_clauses(nested, words=word_list)
        return nested, clauses

    def _split_internal_markers(self, phrases: List[Phrase]) -> List[Phrase]:
        """If a VP contains a clause marker not only as a trailing shell, split.

        Phrase rules like ``VERB PART+`` can pull ``ရွာ သောကြောင့် မ`` into one
        VP; the reason marker must end the REASON clause, with ``မ`` starting
        the next predicate.
        """
        out: List[Phrase] = []
        for p in phrases:
            if p.type not in _VP_LIKE:
                out.append(p)
                continue
            hit = _find_internal_marker(p.tokens, self.clause_rules.markers_longest)
            if hit is None:
                out.append(p)
                continue
            marker, kind, end_tok = hit
            if kind == "relative" and end_tok == len(p.tokens):
                out.append(p)
                continue
            left = _slice_phrase(p, 0, end_tok)
            right = _slice_phrase(p, end_tok, len(p.tokens))
            if left is not None:
                out.append(left)
            if right is not None:
                out.append(right)
        return out

    def _nest_relatives(
        self,
        phrases: List[Phrase],
        *,
        words: Sequence[str],
    ) -> List[Phrase]:
        """Fold relative patterns into one NP with RelativeModifier + HeadNoun.

        Matches YAML ``relative_clause`` patterns (longest first when configured):
        ``VP NP``, ``PP VP NP``, ``NP PP VP NP``, …
        """
        rel = self.clause_rules.kind("relative")
        if rel is None or not rel.markers:
            return list(phrases)
        markers = rel.markers
        patterns = list(rel.phrase_patterns)
        if self.clause_rules.settings.prefer_longest_match:
            patterns.sort(key=lambda p: len(p), reverse=True)

        out: List[Phrase] = []
        i = 0
        n = len(phrases)
        while i < n:
            merged = None
            for pat in patterns:
                hit = self._try_relative_at(phrases, i, pat, markers, words)
                if hit is not None:
                    merged, consume = hit
                    out.append(merged)
                    i += consume
                    break
            if merged is None:
                out.append(phrases[i])
                i += 1
        return out

    def _try_relative_at(
        self,
        phrases: Sequence[Phrase],
        start: int,
        pattern: Sequence[str],
        markers: Sequence[str],
        words: Sequence[str],
    ) -> Optional[Tuple[Phrase, int]]:
        """Try to match *pattern* at *start*; return (merged NP, consume count)."""
        if not pattern or pattern[-1].upper() != "NP":
            return None
        # Exact-length relative templates (no quantifiers in relative_clause V1).
        if any(a.endswith(("*", "+", "?")) for a in pattern):
            return None
        width = len(pattern)
        if start + width > len(phrases):
            return None
        window = phrases[start : start + width]
        labels = [_label(p) for p in window]
        expected = [a.upper().strip("()") for a in pattern]
        # Expand simple alts like NP|PP in a single atom without quant.
        for lab, exp in zip(labels, expected):
            alts = {x.strip() for x in exp.split("|")}
            if lab not in alts:
                return None
        head = window[-1]
        if head.type != ChunkType.NOUN_PHRASE:
            return None
        # Relative-marked VP is the last VP-like phrase before the head.
        vp_idx = None
        for j in range(len(window) - 2, -1, -1):
            if window[j].type in _VP_LIKE:
                vp_idx = j
                break
        if vp_idx is None:
            return None
        vp = window[vp_idx]
        gap = _gap_text(words, vp.end + 1, head.start)
        if not (
            _ends_with_any(vp.tokens, markers) or _text_is_marker(gap, markers)
        ):
            return None

        mod_phrases = list(window[:-1])
        mod_tokens: List[str] = []
        mod_tags: List[str] = []
        for mp in mod_phrases:
            mod_tokens.extend(mp.tokens)
            mod_tags.extend(mp.pos_tags)
        mod_text = "".join(p.text for p in mod_phrases)
        mod_end = mod_phrases[-1].end
        if gap and _text_is_marker(gap, markers):
            gap_toks = list(words[vp.end + 1 : head.start])
            mod_tokens = mod_tokens + gap_toks
            mod_tags = mod_tags + [""] * len(gap_toks)
            mod_text = mod_text + gap
            mod_end = head.start - 1

        # RelativeModifier children preserve the pre-head phrase hierarchy.
        mod_children = tuple(
            Phrase(
                type=mp.type,
                text=mp.text,
                tokens=list(mp.tokens),
                pos_tags=list(mp.pos_tags),
                start=mp.start,
                end=mp.end,
                grammatical_function=mp.grammatical_function,
                semantic_role=mp.semantic_role,
                role=None,
                children=mp.children,
                features=dict(mp.features),
            )
            for mp in mod_phrases
        )
        mod = Phrase(
            type=ChunkType.VERB_PHRASE if len(mod_phrases) == 1 and mod_phrases[0].type in _VP_LIKE else ChunkType.VERB_PHRASE,
            text=mod_text,
            tokens=mod_tokens,
            pos_tags=mod_tags,
            start=mod_phrases[0].start,
            end=mod_end,
            grammatical_function="MODIFIER",
            semantic_role=None,
            role=ROLE_RELATIVE_MODIFIER,
            children=mod_children if len(mod_children) > 1 else (),
            features={"clause": "RELATIVE"},
        )
        # Prefer keeping a single-VP modifier as the VP itself (no wrapper).
        if len(mod_phrases) == 1 and mod_phrases[0].type in _VP_LIKE and not gap:
            mod = Phrase(
                type=mod_phrases[0].type,
                text=mod_text,
                tokens=mod_tokens,
                pos_tags=mod_tags,
                start=mod_phrases[0].start,
                end=mod_end,
                grammatical_function="MODIFIER",
                semantic_role=mod_phrases[0].semantic_role,
                role=ROLE_RELATIVE_MODIFIER,
                children=(),
                features={"clause": "RELATIVE"},
            )
        elif len(mod_phrases) == 1 and mod_phrases[0].type in _VP_LIKE and gap:
            mod = Phrase(
                type=mod_phrases[0].type,
                text=mod_text,
                tokens=mod_tokens,
                pos_tags=mod_tags,
                start=mod_phrases[0].start,
                end=mod_end,
                grammatical_function="MODIFIER",
                semantic_role=mod_phrases[0].semantic_role,
                role=ROLE_RELATIVE_MODIFIER,
                children=(),
                features={"clause": "RELATIVE"},
            )

        head_node = Phrase(
            type=head.type,
            text=head.text,
            tokens=list(head.tokens),
            pos_tags=list(head.pos_tags),
            start=head.start,
            end=head.end,
            grammatical_function=head.grammatical_function,
            semantic_role=head.semantic_role,
            role=ROLE_HEAD_NOUN,
            children=(),
            features=dict(head.features),
        )
        merged = Phrase(
            type=ChunkType.NOUN_PHRASE,
            text=mod_text + head.text,
            tokens=mod_tokens + list(head.tokens),
            pos_tags=mod_tags + list(head.pos_tags),
            start=mod_phrases[0].start,
            end=head.end,
            grammatical_function=head.grammatical_function,
            semantic_role=head.semantic_role,
            role=None,
            children=(mod, head_node),
            features={"relative": "true"},
        )
        return merged, width

    def _cut_clauses(
        self,
        phrases: List[Phrase],
        *,
        words: Sequence[str],
    ) -> List[Clause]:
        """Emit top-level clauses (never RELATIVE)."""
        if not phrases:
            return []

        clauses: List[Clause] = []
        cursor = 0
        n = len(phrases)
        settings = self.clause_rules.settings

        while cursor < n:
            hit = self._find_marked_clause(phrases, cursor, words=words)
            if hit is None:
                break
            _start_i, end_i, kind_name, marker = hit
            kind = self.clause_rules.kind(kind_name)
            if kind is None:
                cursor = end_i + 1
                continue

            span = phrases[cursor : end_i + 1]
            # PURPOSE heuristic: NP before VP → PURPOSE clause; else Purpose VP
            # TODO(V2): richer subject / control detection for ရန် / ဖို့.
            if kind.clause_type == ClauseType.PURPOSE:
                if not any(p.type == ChunkType.NOUN_PHRASE for p in span[:-1]):
                    phrases[end_i] = _with_role(
                        phrases[end_i],
                        role="PurposeVP",
                        features={"marker": marker, "purpose_vp": "true"},
                    )
                    cursor = end_i + 1
                    continue

            if kind.nesting or kind.clause_type not in TOP_LEVEL_CLAUSE_TYPES:
                cursor = end_i + 1
                continue

            if settings.require_final_vp and not _has_predicate(span):
                cursor = end_i + 1
                continue

            if not self._matches_patterns(span, kind.phrase_patterns):
                if not span or span[-1].type not in _VP_LIKE:
                    cursor = end_i + 1
                    continue

            clauses.append(
                _make_clause(
                    kind.clause_type,
                    span,
                    marker=marker,
                    relation=kind.relation,
                )
            )
            cursor = end_i + 1

        if cursor < n:
            rest = phrases[cursor:]
            main = self.clause_rules.kind("main")
            # Residual span only — subordinate markers with higher precedence
            # have already claimed their boundaries above.
            if is_valid_main_clause(
                rest,
                end_markers=(main.end_markers if main else ()),
                phrase_patterns=(main.phrase_patterns if main else ()),
                pattern_matcher=self._pattern_matcher,
                require_final_vp=settings.require_final_vp,
            ):
                clauses.append(
                    _make_clause(
                        ClauseType.MAIN,
                        rest,
                        relation=(main.relation if main else "matrix"),
                    )
                )

        return clauses

    def _matches_patterns(
        self,
        phrases: Sequence[Phrase],
        patterns: Sequence[Tuple[str, ...]],
    ) -> bool:
        labels = [_label(p) for p in phrases]
        return self._pattern_matcher.matches(labels, patterns)

    def _find_marked_clause(
        self,
        phrases: Sequence[Phrase],
        start: int,
        *,
        words: Sequence[str] = (),
    ) -> Optional[Tuple[int, int, str, str]]:
        """Leftmost VP (from *start*) ending with / followed by a marker.

        Returns ``(clause_start, vp_index, kind_name, marker)``.
        Relative markers are skipped (handled by nesting).
        """
        rel = self.clause_rules.kind("relative")
        rel_set = set(rel.markers) if rel else set()

        for i in range(start, len(phrases)):
            p = phrases[i]
            if p.type not in _VP_LIKE:
                continue
            if p.role == ROLE_RELATIVE_MODIFIER:
                continue
            matched = _match_end_marker(p.tokens, self.clause_rules.markers_longest)
            if matched is None and words:
                gap_end = (
                    phrases[i + 1].start if i + 1 < len(phrases) else len(words)
                )
                gap = _gap_text(words, p.end + 1, gap_end)
                for marker, kind in self.clause_rules.markers_longest:
                    if gap == marker:
                        matched = (marker, kind)
                        break
            if matched is None:
                continue
            marker, kind_name = matched
            if kind_name == "relative" or marker in rel_set:
                continue
            return start, i, kind_name, marker
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_internal_marker(
    tokens: Sequence[str],
    markers_longest: Sequence[Tuple[str, str]],
) -> Optional[Tuple[str, str, int]]:
    if not tokens:
        return None
    best: Optional[Tuple[int, int, str, str]] = None
    n = len(tokens)
    for i in range(n):
        for marker, kind in markers_longest:
            end = _match_joined_from(tokens, i, marker)
            if end is None:
                continue
            if best is None or i < best[0] or (i == best[0] and end > best[1]):
                best = (i, end, marker, kind)
        if best is not None and best[0] == i:
            break
    if best is None:
        return None
    _i, end, marker, kind = best
    return marker, kind, end


def _match_joined_from(
    tokens: Sequence[str], start: int, text: str
) -> Optional[int]:
    acc = ""
    for j in range(start, len(tokens)):
        acc += tokens[j]
        if acc == text:
            return j + 1
        if not text.startswith(acc):
            return None
    return None


def _slice_phrase(phrase: Phrase, start: int, end: int) -> Optional[Phrase]:
    if end <= start:
        return None
    toks = list(phrase.tokens[start:end])
    tags = list(phrase.pos_tags[start:end])
    if not toks:
        return None
    abs_start = phrase.start + start
    abs_end = phrase.start + end - 1
    return Phrase(
        type=phrase.type,
        text="".join(toks),
        tokens=toks,
        pos_tags=tags,
        start=abs_start,
        end=abs_end,
        grammatical_function=phrase.grammatical_function,
        semantic_role=phrase.semantic_role,
        role=phrase.role,
        children=(),
        features=dict(phrase.features),
    )


def _gap_text(words: Sequence[str], start: int, end: int) -> str:
    if start >= end or start < 0 or end > len(words):
        return ""
    return "".join(words[start:end])


def _text_is_marker(text: str, markers: Sequence[str]) -> bool:
    if not text:
        return False
    return text in set(markers)


def _ends_with_any(tokens: Sequence[str], markers: Sequence[str]) -> bool:
    if not tokens or not markers:
        return False
    joined = "".join(tokens)
    for m in sorted(markers, key=len, reverse=True):
        if joined.endswith(m):
            return True
        acc = ""
        for t in reversed(tokens):
            acc = t + acc
            if acc == m:
                return True
            if not m.endswith(acc):
                break
    return False


def _match_end_marker(
    tokens: Sequence[str],
    markers_longest: Sequence[Tuple[str, str]],
) -> Optional[Tuple[str, str]]:
    if not tokens:
        return None
    joined = "".join(tokens)
    for marker, kind in markers_longest:
        if joined.endswith(marker):
            return marker, kind
        acc = ""
        for t in reversed(tokens):
            acc = t + acc
            if acc == marker:
                return marker, kind
            if not marker.endswith(acc):
                break
    return None


def _label(p: Phrase) -> str:
    return _TYPE_LABEL.get(p.type, p.type.value)


def _has_predicate(phrases: Sequence[Phrase]) -> bool:
    return any(p.type in _VP_LIKE for p in phrases)


def _final_vp(phrases: Sequence[Phrase]) -> Optional[Phrase]:
    """Rightmost VP-like phrase; MAIN must end on this constituent."""
    for p in reversed(phrases):
        if p.type in _VP_LIKE:
            return p
    return None


def _detect_sentence_marker(
    final_vp: Phrase, end_markers: Sequence[str]
) -> str:
    """Longest end_marker that suffixes the final VP token stream (or "")."""
    if not final_vp.tokens or not end_markers:
        return ""
    joined = "".join(final_vp.tokens)
    for marker in sorted(end_markers, key=len, reverse=True):
        if joined.endswith(marker):
            return marker
        acc = ""
        for t in reversed(final_vp.tokens):
            acc = t + acc
            if acc == marker:
                return marker
            if not marker.endswith(acc):
                break
    return ""


def is_valid_main_clause(
    phrase_sequence: Sequence[Phrase],
    final_vp: Optional[Phrase] = None,
    sentence_marker: str = "",
    *,
    end_markers: Sequence[str] = (),
    phrase_patterns: Sequence[Tuple[str, ...]] = (),
    pattern_matcher: Optional[PhrasePatternMatcher] = None,
    require_final_vp: bool = True,
) -> bool:
    """Return True only when a MAIN clause is fully licensed.

    A Main Clause is **never** emitted from a bare end-marker (သည် / ပြီ /
    ပါ / …) alone. All of the following must hold:

    1. The span ends with a valid VP (or a GREETING utterance).
    2. That VP contains a recognised sentence-final marker (unless GREETING).
    3. The phrase sequence matches a permitted clause template.
    4. Callers must only pass residual spans after higher-precedence
       subordinate markers have already claimed their boundaries.

    Parameters
    ----------
    phrase_sequence:
        Ordered phrase chunks for the candidate MAIN span.
    final_vp:
        Optional precomputed final VP; discovered automatically when omitted.
    sentence_marker:
        Optional known end marker; verified against *end_markers* / VP text.
    """
    if not phrase_sequence:
        return False

    matcher = pattern_matcher or default_pattern_matcher()
    labels = [_label(p) for p in phrase_sequence]

    # GREETING is a complete utterance without finite particles.
    if any(p.type == ChunkType.GREETING for p in phrase_sequence):
        if phrase_patterns and not matcher.matches(labels, phrase_patterns):
            # Still allow a lone GREETING chunk.
            if not (
                len(phrase_sequence) == 1
                and phrase_sequence[0].type == ChunkType.GREETING
            ):
                return False
        return True

    vp = final_vp if final_vp is not None else _final_vp(phrase_sequence)
    if require_final_vp and vp is None:
        return False
    if vp is None:
        return False

    # Constituent must end with the VP (no trailing NP/PP after the predicate).
    if phrase_sequence[-1] is not vp and phrase_sequence[-1].type not in _VP_LIKE:
        # Allow only if last is also VP-like (shouldn't happen); otherwise fail.
        if phrase_sequence[-1].type not in _VP_LIKE:
            return False

    marker = sentence_marker or _detect_sentence_marker(vp, end_markers)
    if end_markers:
        if not marker or marker not in set(end_markers):
            return False
        if not _ends_with_any(vp.tokens, (marker,)):
            return False
    else:
        # No inventory configured — still refuse marker-only / non-VP spans.
        if not _has_predicate(phrase_sequence):
            return False

    if phrase_patterns and not matcher.matches(labels, phrase_patterns):
        return False

    return True


def _with_role(
    phrase: Phrase, *, role: str, features: Optional[dict] = None
) -> Phrase:
    feats = dict(phrase.features)
    if features:
        feats.update(features)
    return Phrase(
        type=phrase.type,
        text=phrase.text,
        tokens=list(phrase.tokens),
        pos_tags=list(phrase.pos_tags),
        start=phrase.start,
        end=phrase.end,
        grammatical_function=phrase.grammatical_function,
        semantic_role=phrase.semantic_role,
        role=role,
        children=phrase.children,
        features=feats,
    )


def _make_clause(
    ctype: ClauseType,
    phrases: Sequence[Phrase],
    *,
    marker: str = "",
    relation: str = "",
) -> Clause:
    feats = {}
    if marker:
        feats["marker"] = marker
    if relation:
        feats["relation"] = relation
    return Clause(
        type=ctype,
        text="".join(p.text for p in phrases),
        phrases=tuple(phrases),
        start=phrases[0].start,
        end=phrases[-1].end,
        relation=relation or None,
        marker=marker,
        features=feats,
    )


def load_clause_markers(directory=None):
    from .rules import grammar_dir, load_clause_rules

    d = directory or grammar_dir()
    path = d / "clause_rules.yml"
    if path.is_file():
        return load_clause_rules(path).marker_texts()
    from .rules import load_markers

    return load_markers(d / "phrase_markers.yml").all_clause_markers()
