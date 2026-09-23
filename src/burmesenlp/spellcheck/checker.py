# -*- coding: utf-8 -*-
"""Norvig-style spell-checking for already-segmented Burmese words.

Candidate generation (delete/transpose/replace/insert) runs at the
Unicode **codepoint** level, not the syllable level: the realistic
Burmese typo is a dropped, swapped, or wrong combining mark (asat,
medial, vowel sign) within a syllable cluster, and codepoint-level edits
catch that directly -- a syllable-level edit distance would not.

Every lexicon word and every query word is run through
``canonical_order()`` before comparison. The bundled lexicon stores
words in whatever mark order its source data happened to use, which is
not guaranteed to be Table 16-4 canonical order; a query typed in a
*different*, equally valid mark order for the same word must not be
flagged as a typo and "corrected" into a different word (the exact
degenerate-string problem ``canonical_order()`` exists to fix
elsewhere -- see ``burmesenlp.normalize``). Canonicalizing only the
query and comparing against non-canonicalized lexicon keys would not
fully solve this, since the lexicon's own stored order might not match
either; canonicalizing both sides is what actually closes the gap.
"""
from __future__ import annotations

from functools import lru_cache
from typing import FrozenSet, Iterable, List, Optional, Sequence, Set, Tuple

from ..lexicon import Lexicon
from ..normalize import canonical_order, normalize

__all__ = ["is_known", "suggest", "correct_words"]


def _require_str(value: object, what: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{what} must be a str, got {type(value).__name__}")
    return value


def _canonicalize(word: str) -> str:
    return canonical_order(normalize(word, warn_zawgyi=False))


@lru_cache(maxsize=8)
def _canonical_words(lexicon: Lexicon) -> FrozenSet[str]:
    """Every lexicon entry, canonicalized. Cached per *lexicon instance*.

    ``Lexicon.default()`` builds a fresh object on every call (same as
    ``pos_tag()``'s own default), so this cache only pays off when a
    caller builds one ``Lexicon`` and reuses it across calls -- still
    worth it for that case, free otherwise.
    """
    return frozenset(canonical_order(w) for w in lexicon.words())


@lru_cache(maxsize=8)
def _alphabet(lexicon: Lexicon) -> Tuple[str, ...]:
    """Distinct codepoints seen anywhere in *lexicon*'s words.

    Used to generate insert/replace edit candidates -- bounded by the
    Myanmar script's actual repertoire (consonants, medials, vowel
    signs, digits, a handful of punctuation marks), not the whole of
    Unicode.
    """
    chars: Set[str] = set()
    for word in lexicon.words():
        chars.update(word)
    return tuple(sorted(chars))


def _edits1(word: str, alphabet: Sequence[str]) -> Set[str]:
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes = (a + b[1:] for a, b in splits if b)
    transposes = (a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1)
    replaces = (a + c + b[1:] for a, b in splits if b for c in alphabet)
    inserts = (a + c + b for a, b in splits for c in alphabet)
    return set(deletes) | set(transposes) | set(replaces) | set(inserts)


def _edits2(word: str, alphabet: Sequence[str]) -> Set[str]:
    return {e2 for e1 in _edits1(word, alphabet) for e2 in _edits1(e1, alphabet)}


def _known(candidates: Iterable[str], canonical_words: FrozenSet[str]) -> Set[str]:
    return {c for c in candidates if c in canonical_words}


def _suggest_canonical(
    key: str,
    canonical_words: FrozenSet[str],
    alphabet: Tuple[str, ...],
    max_suggestions: int,
) -> List[str]:
    if not key or key in canonical_words:
        return []
    candidates = _known(_edits1(key, alphabet), canonical_words)
    if not candidates:
        candidates = _known(_edits2(key, alphabet), canonical_words)
    return sorted(candidates)[:max_suggestions]


def is_known(word: str, *, lexicon: Optional[Lexicon] = None) -> bool:
    """True if *word* (any valid mark order) is in *lexicon*.

    Compares canonicalized forms on both sides -- see the module
    docstring for why. Defaults to :meth:`Lexicon.default`.
    """
    _require_str(word, "word")
    lex = lexicon if lexicon is not None else Lexicon.default()
    return _canonicalize(word) in _canonical_words(lex)


def suggest(
    word: str,
    *,
    max_suggestions: int = 5,
    lexicon: Optional[Lexicon] = None,
) -> List[str]:
    """Ranked correction candidates for *word*, or ``[]`` if already known.

    Tries edit distance 1 first (dropped/swapped/extra/wrong mark or
    consonant); falls back to edit distance 2 only if nothing at
    distance 1 is a known word. Candidates are canonicalized lexicon
    entries -- not necessarily the exact string the lexicon stores --
    since re-deriving one specific mark order is not the goal here.
    Ties are broken alphabetically; the bundled lexicon carries no
    frequency data to rank by (see the project plan for this being a
    known v1 limitation, not an oversight).
    """
    _require_str(word, "word")
    if max_suggestions < 1:
        raise ValueError(f"max_suggestions must be >= 1, got {max_suggestions}")
    lex = lexicon if lexicon is not None else Lexicon.default()
    key = _canonicalize(word)
    return _suggest_canonical(key, _canonical_words(lex), _alphabet(lex), max_suggestions)


def correct_words(
    words: Sequence[str],
    *,
    lexicon: Optional[Lexicon] = None,
) -> List[str]:
    """Apply the top :func:`suggest` candidate to each unknown word.

    A word with no in-budget suggestion is returned unchanged (never
    dropped or replaced with a guess outside the edit-distance-2
    budget). *words* is a pre-segmented word list, e.g. the output of
    :func:`burmesenlp.word_tokenize` -- Burmese has no spaces, so
    correcting raw, unsegmented text is not a well-formed operation
    here, the same reason :func:`burmesenlp.pos_tag` also takes a word
    list rather than a sentence.
    """
    if not isinstance(words, (list, tuple)):
        raise TypeError(f"words must be a list of str, got {type(words).__name__}")
    lex = lexicon if lexicon is not None else Lexicon.default()
    canonical_words = _canonical_words(lex)
    alphabet = _alphabet(lex)

    corrected: List[str] = []
    for word in words:
        _require_str(word, "each word")
        key = _canonicalize(word)
        if key in canonical_words:
            corrected.append(word)
            continue
        candidates = _suggest_canonical(key, canonical_words, alphabet, max_suggestions=1)
        corrected.append(candidates[0] if candidates else word)
    return corrected
