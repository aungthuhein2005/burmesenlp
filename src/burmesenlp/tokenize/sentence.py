"""Grammar-aware sentence segmentation over phrase chunks.

Pipeline placement (v1):
    normalize → words → BMWE → POS → phrase chunks → **sentences**
    → typed clause overlays (per sentence)

Design rules
------------
1. Never split merely because a token equals သည် / တယ် / ပါ.  Those are
   particles whose role depends on POS (POSTP subject marker vs SFP).
2. A sentence is complete only after a predicate phrase (VP / FIXED_VERB /
   GREETING) has been observed — typically the Burmese pattern
   ``NP* PP* VP`` (multiple NPs allowed before the predicate).
3. Split when:
   - terminal punctuation (။ ? ! …) is seen, or
   - end of document, or
   - a completed *finite* predicate is followed by a new sentence onset
     (NP / GREETING / …) when soft-splitting is enabled.
4. Do **not** split after an isolated NP / PP / FIXED_EXPRESSION alone.
5. Do **not** treat politeness / finite particles (ပါတယ်, ပါဘူး, …) as
   sentence onsets even if mistagged as NOUN.
6. Consume non-overlapping phrase chunks (clause overlays ignored);
   uncovered tokens become singleton units so the covering is complete.

``split_on_final_particles`` is retained for API compatibility: when
False, soft splits after a completed VP (without punctuation) are
disabled; punctuation and end-of-document splits remain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple, Union

from .. import grammar
from ..chunking.models import Chunk, ChunkType, is_clause_type
from .syllable import FULL_STOP, SECTION, Token


_TERMINAL_PUNCT = frozenset(".!?\u2026")

# Phrase types that count as a completed predicate / utterance.
_PREDICATE_TYPES = frozenset(
    {
        ChunkType.VERB_PHRASE,
        ChunkType.FIXED_VERB,
        ChunkType.GREETING,
    }
)

# Phrase types that typically open a new sentence after a predicate.
_ONSET_TYPES = frozenset(
    {
        ChunkType.NOUN_PHRASE,
        ChunkType.GREETING,
        ChunkType.NUMERAL_PHRASE,
    }
)

# Surfaces that look like NP onsets when mistagged but belong to the VP tail.
_FALSE_ONSET_SURFACES = frozenset(
    {
        "ပါတယ်",
        "ပါဘူး",
        "ချင်ပါတယ်",
        "သည်",
        "တယ်",
        "မည်",
        "ပြီ",
        "ပါ",
        "ဘူး",
        "လား",
        "မလား",
    }
)

_CONTINUATION_SURFACES = (
    grammar.POST_FINAL_CONTINUATIONS
    | grammar.CONJUNCTIONS
    | frozenset({"ပေမဲ့", "ဒါပေမယ့်", "သော်လည်း", "သို့သော်", "လို့", "ဆို", "ဆိုတဲ့"})
)


def _is_terminal_punct(text: str) -> bool:
    return bool(text) and all(c in _TERMINAL_PUNCT for c in text)


@dataclass(frozen=True)
class Sentence:
    text: str
    start: int
    end: int
    words: Tuple[Token, ...] = ()
    word_start: int = 0  # inclusive index into post-MWE word list
    word_end: int = 0  # exclusive index into post-MWE word list


@dataclass(frozen=True)
class _Unit:
    """One covering span over the post-MWE token stream."""

    start: int
    end: int  # inclusive
    ctype: Optional[ChunkType]
    is_punct: bool


class SentenceSegmenter:
    """Chunk/POS-aware sentence segmenter.

    Preferred entry point: :meth:`segment_from_chunks`.
    :meth:`segment` remains as a punctuation-only fallback when chunks
    are unavailable (legacy Token stream).
    """

    def __init__(self, split_on_final_particles: bool = True):
        # Soft-split after completed VP before a new onset (no ။ required).
        self.split_on_final_particles = split_on_final_particles

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def segment_from_chunks(
        self,
        words: Sequence[str],
        pos_tags: Sequence[Union[str, Tuple[str, str]]],
        chunks: Sequence[Chunk],
        text: str,
        *,
        char_spans: Optional[Sequence[Tuple[int, int]]] = None,
    ) -> List[Sentence]:
        """Segment using phrase chunks over *words* / *pos_tags*.

        *char_spans[i]* is ``(start, end)`` into *text* for ``words[i]``.
        When omitted, sentences are built by joining word strings (offsets
        are approximate / zero).
        """
        words = list(words)
        tags = [_tag_str(t) for t in pos_tags]
        if len(words) != len(tags):
            raise ValueError(
                f"words/pos_tags length mismatch: {len(words)} != {len(tags)}"
            )
        if not words:
            return []

        units = _covering_units(words, tags, chunks)
        # Exclusive word-index cuts (end of each sentence).
        cuts = self._boundary_cuts(units, words, tags)
        return _sentences_from_cuts(words, text, cuts, char_spans)

    def segment(self, word_tokens: Sequence[Token], text: str) -> List[Sentence]:
        """Legacy fallback: punctuation-only splits over word Tokens.

        Does **not** split on သည်/တယ်/ပါ.  Prefer
        :meth:`segment_from_chunks` in the full pipeline.
        """
        sentences: List[Sentence] = []
        current: List[Token] = []
        for w in word_tokens:
            current.append(w)
            if w.text == FULL_STOP or _is_terminal_punct(w.text):
                sentences.append(self._build_from_tokens(current, text))
                current = []
        if current:
            sentences.append(self._build_from_tokens(current, text))
        return sentences

    # ------------------------------------------------------------------
    # Boundary detection
    # ------------------------------------------------------------------

    def _boundary_cuts(
        self,
        units: Sequence[_Unit],
        words: Sequence[str],
        tags: Sequence[str],
    ) -> List[int]:
        """Return exclusive word indices where sentences end."""
        cuts: List[int] = []
        seen_predicate = False
        n = len(units)

        for ui, unit in enumerate(units):
            nxt = units[ui + 1] if ui + 1 < n else None

            # Rule 3: terminal punctuation ends the sentence.
            if unit.is_punct:
                cuts.append(unit.end + 1)
                seen_predicate = False
                continue

            # Track predicates (VP / FIXED_VERB / GREETING).
            if unit.ctype in _PREDICATE_TYPES:
                seen_predicate = True
                # Soft split: completed finite VP followed by a new onset
                # (no punctuation).  Disabled when split_on_final_particles
                # is False (API-compatible "punctuation only" mode).
                if (
                    self.split_on_final_particles
                    and nxt is not None
                    and not nxt.is_punct
                    and _predicate_is_finite(unit, words, tags)
                    and _is_sentence_onset(nxt, words, tags)
                    and not _is_continuation(nxt, words, tags)
                ):
                    cuts.append(unit.end + 1)
                    seen_predicate = False
                continue

            # SFP / PART tokens after a VP (often uncovered by phrase
            # patterns) still belong to the current sentence; absorb them
            # and soft-split only when the following unit starts a new NP.
            if (
                self.split_on_final_particles
                and seen_predicate
                and nxt is not None
                and not nxt.is_punct
                and _unit_is_sfp_tail(unit, tags)
                and _is_sentence_onset(nxt, words, tags)
                and not _is_continuation(nxt, words, tags)
            ):
                cuts.append(unit.end + 1)
                seen_predicate = False
                continue

            # NP / PP / FIXED_EXPRESSION / OTHER: never force a split
            # (Rules 1, 4, 5).

        # Rule 3: end of document.
        if not cuts or cuts[-1] != (units[-1].end + 1 if units else 0):
            end = (units[-1].end + 1) if units else 0
            if not cuts or cuts[-1] != end:
                cuts.append(end)
        return cuts

    @staticmethod
    def _build_from_tokens(tokens: List[Token], text: str) -> Sentence:
        start = tokens[0].start
        end = tokens[-1].end
        return Sentence(
            text=text[start:end],
            start=start,
            end=end,
            words=tuple(tokens),
            word_start=0,
            word_end=0,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tag_str(tag: Union[str, Tuple[str, str]]) -> str:
    if isinstance(tag, tuple):
        return tag[1]
    return tag


def _covering_units(
    words: Sequence[str],
    tags: Sequence[str],
    chunks: Sequence[Chunk],
) -> List[_Unit]:
    """Build a complete, non-overlapping covering of the token stream."""
    # Ignore clause overlays — phrase layer is the segmentation substrate.
    phrase = sorted(
        (c for c in chunks if not is_clause_type(c.type)),
        key=lambda c: (c.start, -(c.end - c.start)),
    )
    # Drop overlaps (keep first / longest-first already sorted).
    selected: List[Chunk] = []
    covered = [False] * len(words)
    for c in phrase:
        if any(covered[j] for j in range(c.start, c.end + 1)):
            continue
        for j in range(c.start, c.end + 1):
            covered[j] = True
        selected.append(c)
    selected.sort(key=lambda c: c.start)

    units: List[_Unit] = []
    i = 0
    n = len(words)
    ci = 0
    while i < n:
        if ci < len(selected) and selected[ci].start == i:
            c = selected[ci]
            units.append(
                _Unit(
                    start=c.start,
                    end=c.end,
                    ctype=c.type,
                    is_punct=_span_is_punct(tags, c.start, c.end),
                )
            )
            i = c.end + 1
            ci += 1
            continue
        if ci < len(selected) and selected[ci].start < i:
            ci += 1
            continue
        # Uncovered token → singleton unit.
        units.append(
            _Unit(
                start=i,
                end=i,
                ctype=None,
                is_punct=_span_is_punct(tags, i, i)
                or words[i] == FULL_STOP
                or words[i] == SECTION
                or _is_terminal_punct(words[i]),
            )
        )
        i += 1
    return units


def _span_is_punct(tags: Sequence[str], start: int, end: int) -> bool:
    return all(tags[j] == "PUNCT" for j in range(start, end + 1))


def _is_sentence_onset(
    unit: _Unit,
    words: Sequence[str],
    tags: Sequence[str],
) -> bool:
    surface = words[unit.start]
    if surface in _FALSE_ONSET_SURFACES:
        return False
    if tags[unit.start] in {"SFP", "PART", "AUX", "CONJ", "POSTP", "PUNCT"}:
        return False
    if unit.ctype in _ONSET_TYPES:
        return True
    # Bare pronoun / noun starting a new clause after a predicate.
    if unit.ctype is None and tags[unit.start] in {"PRON", "NOUN", "NUM"}:
        return True
    return False


def _is_continuation(
    unit: _Unit,
    words: Sequence[str],
    tags: Sequence[str],
) -> bool:
    """True when the next unit continues the current sentence (conj / quotative)."""
    if words[unit.start] in _CONTINUATION_SURFACES:
        return True
    if tags[unit.start] == "CONJ":
        return True
    return False


def _predicate_is_finite(
    unit: _Unit,
    words: Sequence[str],
    tags: Sequence[str],
) -> bool:
    """Require finite/politeness evidence before soft-splitting after a VP.

    Bare VERB / VERB+AUX stems (သွားခဲ့) must not soft-split before a following
    ပါတယ် that was mistagged as NOUN — the politeness particle belongs to
    this sentence.
    """
    for j in range(unit.end, unit.start - 1, -1):
        if tags[j] in {"SFP", "PART"}:
            return True
        if words[j] in _FALSE_ONSET_SURFACES:
            return True
        if tags[j] in {"VERB", "AUX", "IDIOM"}:
            # Keep scanning left through the verbal nucleus.
            continue
        break
    return False


def _unit_is_sfp_tail(unit: _Unit, tags: Sequence[str]) -> bool:
    return unit.ctype is None and all(
        tags[j] in {"SFP", "PART", "AUX"} for j in range(unit.start, unit.end + 1)
    )


def _sentences_from_cuts(
    words: Sequence[str],
    text: str,
    cuts: Sequence[int],
    char_spans: Optional[Sequence[Tuple[int, int]]],
) -> List[Sentence]:
    """Turn exclusive word-index cuts into Sentence objects that partition *text*."""
    if not words:
        return []
    if not cuts:
        cuts = [len(words)]

    # Word-index ranges.
    ranges: List[Tuple[int, int]] = []
    prev = 0
    for cut in cuts:
        if cut <= prev:
            continue
        ranges.append((prev, cut))
        prev = cut
    if prev < len(words):
        ranges.append((prev, len(words)))

    if char_spans is not None and len(char_spans) == len(words):
        # Partition normalized text so ``"".join(sentences) == text``.
        # Interstitial whitespace after ။ attaches to the *following*
        # sentence so sentence text can end with ။ (golden / UX).
        out: List[Sentence] = []
        for i, (a, b) in enumerate(ranges):
            if i == 0:
                start = 0
            else:
                prev_b = ranges[i - 1][1]
                start = char_spans[prev_b - 1][1]
            if i + 1 < len(ranges):
                end = char_spans[b - 1][1]
            else:
                end = len(text)
            out.append(
                Sentence(
                    text=text[start:end],
                    start=start,
                    end=end,
                    word_start=a,
                    word_end=b,
                )
            )
        return out

    # Fallback without char spans: join word texts (no interstitial spaces).
    out = []
    offset = 0
    for a, b in ranges:
        joined = "".join(words[a:b])
        out.append(
            Sentence(
                text=joined,
                start=offset,
                end=offset + len(joined),
                word_start=a,
                word_end=b,
            )
        )
        offset += len(joined)
    return out


def merged_char_spans(
    pre_tokens: Sequence[Token],
    mwe_spans: Sequence[object],
) -> List[Tuple[int, int]]:
    """Map post-MWE word indices to character ``(start, end)`` in the source text."""
    span_by_start = {getattr(s, "start"): s for s in mwe_spans}
    spans: List[Tuple[int, int]] = []
    i = 0
    n = len(pre_tokens)
    while i < n:
        m = span_by_start.get(i)
        if m is not None:
            end_i = getattr(m, "end")
            spans.append((pre_tokens[i].start, pre_tokens[end_i].end))
            i = end_i + 1
        else:
            spans.append((pre_tokens[i].start, pre_tokens[i].end))
            i += 1
    return spans
