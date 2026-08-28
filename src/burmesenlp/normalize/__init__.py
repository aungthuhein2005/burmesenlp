"""Text normalization for Myanmar (Burmese) text."""

from __future__ import annotations

import logging
import re
import unicodedata

logger = logging.getLogger(__name__)

# Zero-width characters that break the segmentation regexes.
_ZERO_WIDTH_TABLE = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff"), None)

# Heuristic only: sequences that are common in Zawgyi-encoded text but
# impossible (or vanishingly rare) in well-formed Unicode Burmese:
#   - code points U+105A / U+1060-U+1097 reused by Zawgyi for glyph variants
#   - vowel-e (U+1031) or medial-ya (U+103B) appearing before any base letter
#   - doubled vowel-e or doubled asat
_ZAWGYI_HINTS = re.compile(
    "[\u105a\u1060-\u1097]"
    "|(?:^|[^\u1000-\u1021\u103a-\u103f])[\u1031\u103b]"
    "|\u1031\u1031"
    "|\u103a\u103a"
)


def looks_like_zawgyi(text: str) -> bool:
    """Heuristically detect Zawgyi-encoded text.

    This is a lightweight rule-based check, not a trained detector.  Use a
    dedicated converter (e.g. ICU transliteration, myanmar-tools) for
    authoritative detection and conversion.
    """
    return bool(_ZAWGYI_HINTS.search(text))


def normalize(text: str, *, warn_zawgyi: bool = True) -> str:
    """Normalize Myanmar text for segmentation.

    - Validates the input type (raises ``TypeError`` for non-``str``).
    - Strips zero-width space/joiner/non-joiner, word-joiner and BOM.
    - Applies Unicode NFC (e.g. composes U+1025 U+102E into U+1026).
    - Logs a warning if the text looks Zawgyi-encoded; conversion to
      Unicode must be done by the caller.  Pass ``warn_zawgyi=False`` when
      normalizing dictionary keys in bulk (avoids noisy false positives).

    NFC does **not** canonicalize Myanmar syllable-mark order: every
    medial/vowel/anusvara/visarga sign has Canonical_Combining_Class 0
    (only asat and dot below are non-zero), so Unicode's canonical
    reordering algorithm never touches their relative order. Two
    different input-method key orders for the same syllable stay
    distinct strings through NFC forever. Call :func:`canonical_order`
    separately (opt-in; not applied here) if that matters for your data.
    """
    if not isinstance(text, str):
        raise TypeError(f"expected str, got {type(text).__name__}")
    if not text:
        return ""
    if warn_zawgyi and looks_like_zawgyi(text):
        logger.warning(
            "Input looks like Zawgyi-encoded text; segmentation results "
            "will be unreliable. Convert to Unicode first."
        )
    text = text.translate(_ZERO_WIDTH_TABLE)
    return unicodedata.normalize("NFC", text)


# ---------------------------------------------------------------------------
# Canonical syllable-mark ordering (Unicode 16.0.0 core spec, Table 16-4,
# "Modern Burmese Syllabic Structure" (kinzi, medials, vowels, finals),
# adjusted for asat: Table 16-4 lists asat's row directly after the
# consonant, before medials -- but that position is only one of three the
# table itself documents as valid (the others: after medial ya; after
# vowel sign tall-aa/aa), and it is empirically NOT the dominant one.
# Cross-checked against the bundled lexicon (every "consonant + medial +
# second consonant + asat" entry has asat last, zero counterexamples) and
# against relative frequency in the myPOS corpus (the asat-last spelling
# of a real collision pair outnumbered the asat-before-medial spelling
# 1061:76) -- both point the same way, so asat is ranked after medials
# and vowel signs here rather than at Table 16-4's literal default spot.
#
# Order used: kinzi < base consonant < stacked consonant <
#             medial ya < medial ra < medial wa < medial ha <
#             vowel e < vowel i/ii/ai < vowel u/uu < vowel tall-aa/aa <
#             asat < anusvara < dot below < visarga
# ---------------------------------------------------------------------------

_KINZI_NGA = "င"  # NGA
_ASAT = "်"
_VIRAMA = "္"

_MEDIAL_RANK = {"ျ": 0, "ြ": 1, "ွ": 2, "ှ": 3}  # ya ra wa ha
_VOWEL_RANK = {
    "ေ": 10,  # e
    "ိ": 11, "ီ": 11, "ဲ": 11,  # i ii ai
    "ု": 12, "ူ": 12,  # u uu
    "ါ": 13, "ာ": 13,  # tall aa, aa
}
# Anusvara(ccc=0)/dot below(ccc=7)/asat(ccc=9)/visarga(ccc=0): dot below
# before asat is not a style choice -- both have non-zero
# Canonical_Combining_Class, so plain NFC already reorders that pair by
# ascending ccc (see Unicode 16.0.0 core spec, Myanmar, Table 16-4
# discussion). Matching that instead of fighting it.
_FINAL_RANK = {"ံ": 20, "့": 21, _ASAT: 22, "း": 23}  # anusvara, dot below, asat, visarga
_MARK_RANK = {**_MEDIAL_RANK, **_VOWEL_RANK, **_FINAL_RANK}
_ORDERABLE_MARKS = set(_MARK_RANK)
_KINZI_CHARS = set(_KINZI_NGA + _ASAT + _VIRAMA)

# Unicode 16.0.0 core spec, Myanmar, "Contractions": a few words repeat a
# consonant sound with one letter + asat rather than writing it twice, so
# asat's position there is a fixed spelling convention, not an encoding
# accident. These are the two sequences the spec documents verbatim;
# recognized as a prefix, they are emitted unchanged and skipped rather
# than rank-sorted, so the empirical medial/vowel/asat ranking above --
# tuned for the ordinary case -- never touches them.
_CONTRACTION_SEQUENCES = (
    "ယောက်ျား",  # man, husband
    "ကျွန်ုပ်",  # I (first person singular)
)


def _is_cluster_base(ch: str) -> bool:
    """True for anything that can start a new syllable cluster.

    Deliberately permissive: any character that is not one of the
    reorderable combining marks and not the virama itself is treated as
    an inert cluster start (base consonant, independent vowel letter,
    punctuation, Latin text, digits, ...), so this function is safe to
    run over mixed running text, not just isolated Myanmar syllables.
    """
    return ch not in _ORDERABLE_MARKS and ch != _VIRAMA


def canonical_order(text: str) -> str:
    """Reorder each Myanmar syllable cluster's marks into Table 16-4 order.

    This is a structural parser, not a sort over the whole string: kinzi
    (``<U+1004, U+103A, U+1039>``, a fixed unit that precedes the base
    consonant it visually sits above) and one stacked/subjoined consonant
    (``<U+1039, consonant>``) are recognized as atomic and left attached
    to their cluster; only the combining marks *within* one cluster
    (asat, medials, vowel signs, anusvara, dot below, visarga) are
    reordered, by rank, among themselves.

    Scope: within one cluster, all reorderable marks (asat included) are
    stable-sorted by a single rank -- see the module-level comment above
    this function for why asat ranks after medials and vowel signs rather
    than at Table 16-4's literal default position. A pathological cluster
    with *two* asat characters keeps them adjacent, in their original
    relative order (stable sort), rather than resolving each to a
    distinct grammatical role. The exception: a documented "Contractions"
    sequence (see ``_CONTRACTION_SEQUENCES``) is recognized and passed
    through unchanged rather than rank-sorted.
    """
    if not text:
        return text
    out = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]

        matched_contraction = next(
            (seq for seq in _CONTRACTION_SEQUENCES if text.startswith(seq, i)),
            None,
        )
        if matched_contraction is not None:
            out.append(matched_contraction)
            i += len(matched_contraction)
            continue

        if ch == _KINZI_NGA and i + 3 <= n and set(text[i : i + 3]) == _KINZI_CHARS:
            out.append(_KINZI_NGA + _ASAT + _VIRAMA)
            i += 3
            continue

        if not _is_cluster_base(ch):
            out.append(ch)  # stray mark with no base in this cluster
            i += 1
            continue

        cluster = [ch]
        i += 1

        if i + 1 < n and text[i] == _VIRAMA and _is_cluster_base(text[i + 1]):
            cluster.append(_VIRAMA + text[i + 1])
            i += 2

        marks = []
        while i < n and text[i] in _ORDERABLE_MARKS:
            marks.append(text[i])
            i += 1
        marks.sort(key=lambda c: _MARK_RANK[c])
        cluster.extend(marks)

        out.append("".join(cluster))

    return "".join(out)
