# -*- coding: utf-8 -*-
"""Auditable Zawgyi -> Unicode conversion with a per-rule repair log.

``zg2uni()`` and ``to_unicode()`` (in ``zawgyi.py``) are unchanged and stay
silent -- they convert or they don't, with no record of what happened.
This module adds a second, opt-in path for callers who need to know
*why*: which of the 118 conversion rules fired, at what offset in the
original text, whether the rule is a plain substitution, a reorder, or a
length change, and whether it is structurally lossy (multiple distinct
Zawgyi inputs collapsing to one Unicode output, so the original glyph
choice cannot be recovered).

Detection uses the calibrated bigram model in ``detector.py`` (not the
fast ``is_zawgyi()`` heuristic), scored per paragraph/segment rather than
once for the whole document -- see CHANGELOG for why a whole-document
score hides mixed-encoding documents. A paragraph is converted only if
its score exceeds ``threshold``.

Position tracking is span-level, not guaranteed character-level: several
rules reorder characters or change the length of the matched text (a
single Zawgyi glyph can expand to a multi-character Unicode sequence), so
a replacement's provenance is recorded as the original-text span its
*entire match* descended from, not a per-output-character mapping.

``ambiguous`` is deliberately always ``False`` in this module: distinguishing
a genuinely ambiguous rule (one where the regex is guessing and could be
wrong for some inputs) from an ordinary substitution requires corpus
evidence -- round-trip testing in both directions across real text -- not
inspection of the rule text. That is follow-up work; this module does not
assert ambiguity it hasn't measured.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import List, Optional, Pattern, Tuple

from ..normalize import canonical_order
from .detector import _split_with_separators, get_zawgyi_probability
from .zawgyi import _zg2uni_rules

_ALT_GROUP = re.compile(r"^\((?:[^()|\\]\|)*[^()|\\]\)$")
_BACKREF = re.compile(r"\\[0-9]")

# Empirically confirmed ambiguous zg2uni rules -- found via round-trip
# testing (uni2zg -> zg2uni on myPOS, canonical_order()+NFC-normalized
# before comparing to avoid counting cosmetic mark-order/precomposition
# differences as failures; see research/zawgyi-repair-log/roundtrip_check.py).
# Distinct from `lossy`: these rules are not structurally many-to-one,
# they are context-sensitive heuristics that guess wrong on some real
# input. Populated only from evidence -- do not add entries without a
# reproducible corpus example.
_EMPIRICALLY_AMBIGUOUS_ZG2UNI_RULES = {
    67: (
        "digit-zero/letter-wa disambiguation heuristic (rules 62-69, 93 "
        "collectively try to guess whether a Zawgyi '၀' glyph is the "
        "digit zero or the letter wa from surrounding context, since the "
        "two render identically); confirmed to misfire on real text where "
        "a genuine decimal-point digit zero sits next to punctuation, e.g. "
        "'6.0%' -- 2/500 myPOS sentences, 3 firings, all wrongly turning a "
        "digit into the letter"
    ),
}


@dataclass(frozen=True)
class RepairEntry:
    """One rule firing that actually changed the text."""

    rule_index: int
    pattern: str
    replacement: str
    matched_text: str
    replacement_text: str
    origin_span: Tuple[int, int]
    category: str  # "substitution" | "reorder" | "length_change"
    lossy: bool
    lossy_note: Optional[str]
    ambiguous: bool = False
    ambiguous_note: Optional[str] = None


@dataclass(frozen=True)
class ParagraphReport:
    text: str
    converted_text: str
    zawgyi_probability: float
    converted: bool
    repairs: List[RepairEntry] = field(default_factory=list)


@dataclass(frozen=True)
class ZawgyiReport:
    text: str
    paragraphs: List[ParagraphReport]
    document_summary: dict


def _rule_is_structurally_lossy(pattern_src: str, replacement: str) -> Optional[str]:
    """Static, corpus-independent check: does this rule collapse >=2
    distinct literal alternatives into one fixed replacement with no
    backreference? If so, the original alternative chosen is not
    recoverable from the output. Returns a note, or None."""
    if _ALT_GROUP.match(pattern_src) and not _BACKREF.search(replacement):
        n_alts = pattern_src.count("|") + 1
        if n_alts > 1:
            alts = pattern_src[1:-1].split("|")
            return (
                f"{n_alts} distinct Zawgyi inputs ({', '.join(alts)}) map to the "
                f"same output {replacement!r}; the original cannot be recovered"
            )
    return None


def _categorize(matched_text: str, replacement_text: str) -> str:
    if len(matched_text) != len(replacement_text):
        return "length_change"
    if sorted(matched_text) == sorted(replacement_text) and matched_text != replacement_text:
        return "reorder"
    return "substitution"


def _apply_rules_with_log(
    text: str,
    rules: List[Tuple[Pattern[str], str]],
    ambiguous_rules: "Optional[dict]" = None,
) -> Tuple[str, List[RepairEntry]]:
    buffer = text
    origin = [(i, i + 1) for i in range(len(text))]
    log: List[RepairEntry] = []
    ambiguous_rules = ambiguous_rules or {}

    for rule_index, (pattern, replacement) in enumerate(rules):
        lossy_note = _rule_is_structurally_lossy(pattern.pattern, replacement)
        ambiguous_note = ambiguous_rules.get(rule_index)
        new_buffer_parts: List[str] = []
        new_origin: List[Tuple[int, int]] = []
        last_end = 0
        for m in pattern.finditer(buffer):
            new_buffer_parts.append(buffer[last_end : m.start()])
            new_origin.extend(origin[last_end : m.start()])

            matched_text = m.group(0)
            replacement_text = m.expand(replacement)

            if m.start() < m.end():
                span_start = origin[m.start()][0]
                span_end = origin[m.end() - 1][1]
            else:
                span_start = span_end = origin[m.start()][0] if m.start() < len(origin) else len(text)

            new_buffer_parts.append(replacement_text)
            new_origin.extend([(span_start, span_end)] * len(replacement_text))

            if replacement_text != matched_text:
                log.append(
                    RepairEntry(
                        rule_index=rule_index,
                        pattern=pattern.pattern,
                        replacement=replacement,
                        matched_text=matched_text,
                        replacement_text=replacement_text,
                        origin_span=(span_start, span_end),
                        category=_categorize(matched_text, replacement_text),
                        lossy=lossy_note is not None,
                        lossy_note=lossy_note,
                        ambiguous=ambiguous_note is not None,
                        ambiguous_note=ambiguous_note,
                    )
                )
            last_end = m.end()

        new_buffer_parts.append(buffer[last_end:])
        new_origin.extend(origin[last_end:])

        buffer = "".join(new_buffer_parts)
        origin = new_origin

    return buffer, log


def _convert_paragraph(text: str, threshold: float, normalize: bool) -> ParagraphReport:
    score = get_zawgyi_probability(text)
    converted = score > threshold
    if converted:
        raw, repairs = _apply_rules_with_log(text, _zg2uni_rules(), _EMPIRICALLY_AMBIGUOUS_ZG2UNI_RULES)
        out = canonical_order(raw)
        if normalize:
            out = unicodedata.normalize("NFC", out)
    else:
        out, repairs = text, []
    return ParagraphReport(
        text=text,
        converted_text=out,
        zawgyi_probability=score,
        converted=converted,
        repairs=repairs,
    )


def convert_with_report(
    text: str, *, threshold: float = 0.5, normalize: bool = True
) -> ZawgyiReport:
    """Convert *text* Zawgyi -> Unicode paragraph-by-paragraph, returning
    the converted text plus a full repair log. Does not affect
    ``to_unicode()``/``zg2uni()``/``process()`` -- this is a separate,
    opt-in API.

    Each paragraph/segment (split on newlines) is scored independently
    with the calibrated bigram detector and converted only if its score
    exceeds *threshold*; a document-level ``min``/``max``/``spread``
    summary is reported instead of a single average, so a document that
    mixes clean and Zawgyi paragraphs doesn't get averaged into a
    misleading single verdict.
    """
    if not isinstance(text, str):
        raise TypeError(f"expected str, got {type(text).__name__}")

    pieces = _split_with_separators(text)
    paragraph_reports: List[ParagraphReport] = []
    rebuilt: List[str] = []

    for i, piece in enumerate(pieces):
        if i % 2 == 1 or not piece.strip():
            rebuilt.append(piece)
            continue
        report = _convert_paragraph(piece, threshold, normalize)
        paragraph_reports.append(report)
        rebuilt.append(report.converted_text)

    scores = [p.zawgyi_probability for p in paragraph_reports if p.zawgyi_probability > float("-inf")]
    summary: dict
    if scores:
        summary = {"min": min(scores), "max": max(scores), "spread": max(scores) - min(scores)}
    else:
        summary = {"min": None, "max": None, "spread": None}

    return ZawgyiReport(
        text="".join(rebuilt),
        paragraphs=paragraph_reports,
        document_summary=summary,
    )


__all__ = ["RepairEntry", "ParagraphReport", "ZawgyiReport", "convert_with_report"]
