"""Spell-checking for already-segmented Burmese words.

Opt-in, self-contained: reuses the existing bundled lexicon
(:meth:`burmesenlp.Lexicon.default`) as its dictionary, no new corpus
or dependency. See :mod:`burmesenlp.spellcheck.checker` for the
codepoint-level edit-distance algorithm and the canonical-mark-order
comparison rationale.

The bundled lexicon is ~24k word-forms; real running text contains
correctly-spelled words outside that set (proper nouns, rare words,
neologisms), so this will have a real false-positive rate on genuine
text -- measured on a 500-sentence Burmese Wikipedia sample, not
assumed: see the CHANGELOG entry for the measured number before relying
on this for anything beyond suggestions a human reviews.
"""
from .checker import correct_words, is_known, suggest

__all__ = ["is_known", "suggest", "correct_words"]
