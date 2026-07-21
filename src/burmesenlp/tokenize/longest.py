"""Greedy longest-match word segmentation engine (``engine=\"longest\"``).

Design decisions (differences from the prototype):

* Matches are aligned to syllable boundaries, so a dictionary word can
  never split a syllable in half.
* Words never merge across whitespace (token adjacency is checked).
* Grammatical suffixes (သည်, များ, ...) are kept as separate word tokens,
  matching the ALT / myPOS corpus convention, instead of being fused onto
  the preceding stem by heuristics.
* The only heuristic merge is numeral/digits + counter classifier
  (e.g. သုံးခု, ၁၂၃ယောက်), which is unambiguous.

Greedy longest match is deterministic and fast but not globally optimal;
for higher accuracy plug in a larger dictionary or a statistical model.
"""

from __future__ import annotations

from typing import List, Sequence

from .. import grammar
from ..lexicon import Lexicon
from .syllable import DIGITS, SYLLABLE, Token

WORD = "word"


class WordSegmenter:
    def __init__(self, lexicon: Lexicon):
        self._lexicon = lexicon

    def segment(self, tokens: Sequence[Token]) -> List[Token]:
        """Group syllable-level tokens into word-level tokens."""
        words: List[Token] = []
        i = 0
        n = len(tokens)
        while i < n:
            tok = tokens[i]

            if tok.kind == DIGITS:
                nxt = tokens[i + 1] if i + 1 < n else None
                if (
                    nxt is not None
                    and nxt.kind == SYLLABLE
                    and nxt.start == tok.end
                    and nxt.text in grammar.COUNTER_CLASSIFIERS
                ):
                    words.append(Token(tok.text + nxt.text, tok.start, nxt.end, WORD))
                    i += 2
                    continue
                words.append(tok)
                i += 1
                continue

            if tok.kind != SYLLABLE:
                words.append(tok)
                i += 1
                continue

            # Collect the contiguous run of adjacent syllables.
            j = i
            while (
                j + 1 < n
                and tokens[j + 1].kind == SYLLABLE
                and tokens[j + 1].start == tokens[j].end
            ):
                j += 1
            words.extend(self._match_run(tokens[i : j + 1]))
            i = j + 1

        return words

    def _match_run(self, run: Sequence[Token]) -> List[Token]:
        out: List[Token] = []
        k = 0
        m = len(run)
        max_syl = self._lexicon.max_word_syllables
        while k < m:
            matched = False
            for length in range(min(max_syl, m - k), 1, -1):
                candidate = "".join(s.text for s in run[k : k + length])
                if candidate in self._lexicon:
                    out.append(
                        Token(candidate, run[k].start, run[k + length - 1].end, WORD)
                    )
                    k += length
                    matched = True
                    break
            if matched:
                continue

            syl = run[k]
            # numeral word + counter classifier -> one word
            if (
                syl.text in grammar.NUMERAL_WORDS
                and k + 1 < m
                and run[k + 1].text in grammar.COUNTER_CLASSIFIERS
            ):
                out.append(
                    Token(syl.text + run[k + 1].text, syl.start, run[k + 1].end, WORD)
                )
                k += 2
                continue

            out.append(Token(syl.text, syl.start, syl.end, WORD))
            k += 1
        return out
