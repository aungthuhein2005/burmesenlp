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
