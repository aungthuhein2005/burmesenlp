"""Sentence segmentation over word tokens.

Boundaries are placed:

* after the Myanmar full stop ။ (and ASCII terminal punctuation . ! ?)
* after a strong sentence-final particle (သည်, တယ်, မည်, ပြီ, လား, မလား)
  when the following word does not continue the clause (quotatives such
  as ဟု / လို့ suppress the split, as does upcoming punctuation).

Unlike the prototype, conjunctions never force a sentence break, and ၏
(mostly a possessive marker) is not a split trigger.

Every sentence carries (start, end) offsets into the normalized text and
the exact word tokens it consists of, so positions and per-sentence tags
can never drift out of sync.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple

from .. import grammar
from .syllable import FULL_STOP, SECTION, Token

_TERMINAL_PUNCT = frozenset(".!?\u2026")


def _is_terminal_punct(text: str) -> bool:
    return bool(text) and all(c in _TERMINAL_PUNCT for c in text)


@dataclass(frozen=True)
class Sentence:
    text: str
    start: int
    end: int
    words: Tuple[Token, ...]


class SentenceSegmenter:
    def __init__(self, split_on_final_particles: bool = True):
        self.split_on_final_particles = split_on_final_particles

    def segment(self, word_tokens: Sequence[Token], text: str) -> List[Sentence]:
        """Group *word_tokens* (offsets into *text*) into sentences."""
        sentences: List[Sentence] = []
        current: List[Token] = []
        n = len(word_tokens)

        for i, w in enumerate(word_tokens):
            current.append(w)
            nxt = word_tokens[i + 1] if i + 1 < n else None

            if w.text == FULL_STOP or _is_terminal_punct(w.text):
                boundary = True
            elif (
                self.split_on_final_particles
                and w.text in grammar.SENTENCE_FINAL_PARTICLES
            ):
                if nxt is None:
                    boundary = True
                else:
                    # Wait for upcoming punctuation; don't split before
                    # quotatives/subordinators that continue the clause.
                    boundary = not (
                        nxt.text == FULL_STOP
                        or nxt.text == SECTION
                        or _is_terminal_punct(nxt.text)
                        or nxt.text in grammar.POST_FINAL_CONTINUATIONS
                    )
            else:
                boundary = False

            if boundary:
                sentences.append(self._build(current, text))
                current = []

        if current:
            sentences.append(self._build(current, text))
        return sentences

    @staticmethod
    def _build(tokens: List[Token], text: str) -> Sentence:
        start = tokens[0].start
        end = tokens[-1].end
        return Sentence(text=text[start:end], start=start, end=end, words=tuple(tokens))
