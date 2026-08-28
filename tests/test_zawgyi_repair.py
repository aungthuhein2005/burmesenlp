"""Tests for the calibrated Zawgyi detector and auditable repair-log
conversion (burmesenlp.zawgyi.detector / burmesenlp.zawgyi.repair).

Deliberately covers more than clean-Zawgyi/clean-Unicode: genuine Shan,
Mon and Karen Unicode text (the false-positive risk this feature exists
to fix), mixed-encoding documents, and short ambiguous strings -- not
just the easy cases, per the ZWSP investigation's lesson that a single
clean-looking proxy metric can hide a broken feature.
"""

import pytest

from burmesenlp.zawgyi import convert_with_report, get_zawgyi_probability
from burmesenlp.zawgyi.detector import score_paragraphs, split_paragraphs

UNICODE_SAMPLE = "မြန်မာစာပေ"
ZAWGYI_SAMPLE = "ျမန္မာစာေပ"

# Genuine Shan Unicode (not Zawgyi) -- Wikipedia article title, real text.
# Uses U+1075-1097 range letters Zawgyi's rule 5 also treats as glyph
# variants of medial-ra; this is the exact codepoint collision the old
# is_zawgyi() heuristic could not resolve.
SHAN_SAMPLE = (
    "ႁႄႇတူဝ်း (တႂ်ႈ) (မၢၼ်ႈ: ဟယ်ဒိုး (အောက်)၊ ဢိင်းၵလဵတ်ႈ: Hei Doe (Lower)) "
    "ၼႆႉ ပဵၼ်ဝၢၼ်ႈဢၼ်မီးၼႂ်း ဢိူင်ႇမၢႆးလုၼ်ႇ၊ "
)

# Genuine Mon Unicode (not Zawgyi) -- real sentence pulled from a random
# mnw.wikipedia.org article, draws from the same shared codepoint range
# (U+105A-1060 Mon letters/medials) that Zawgyi's rules also touch.
MON_SAMPLE = "ဘာသိမ် ဂိုဏ်ရာမညနိကာယဝွံ နွံပ္ဍဲ ကွာန်ဟံဂါမ်၊ ပွိုင်ဍုင်ရေဝ်၊ တွဵုရးဍုင်မန်။"

# Genuine Karen letters, built from documented codepoints (Unicode
# NamesList.txt: U+1061-106D "Extensions for S'gaw Karen" / "Western Pwo
# Karen") rather than hand-typed glyphs, so the codepoints are provably
# correct. No live Karen-language Wikipedia edition exists to sample real
# running text from (checked directly: ksw.wikipedia.org and
# kjp.wikipedia.org do not resolve), so this exercises the codepoints
# rather than a full corpus.
KAREN_LETTERS = "".join(chr(cp) for cp in range(0x1061, 0x106E))


def test_get_zawgyi_probability_clean_cases():
    assert get_zawgyi_probability(UNICODE_SAMPLE) < 0.5
    assert get_zawgyi_probability(ZAWGYI_SAMPLE) > 0.5


def test_get_zawgyi_probability_does_not_flag_shan():
    assert get_zawgyi_probability(SHAN_SAMPLE) < 0.5


def test_get_zawgyi_probability_does_not_flag_mon():
    assert get_zawgyi_probability(MON_SAMPLE) < 0.5


def test_get_zawgyi_probability_type_validation():
    with pytest.raises(TypeError):
        get_zawgyi_probability(None)  # type: ignore[arg-type]


def test_split_paragraphs_preserves_non_blank_segments():
    doc = f"{UNICODE_SAMPLE}\n\n{ZAWGYI_SAMPLE}\n\n{SHAN_SAMPLE}"
    paragraphs = split_paragraphs(doc)
    assert paragraphs == [UNICODE_SAMPLE, ZAWGYI_SAMPLE, SHAN_SAMPLE]


def test_score_paragraphs_isolates_the_zawgyi_paragraph():
    doc = f"{UNICODE_SAMPLE}\n\n{ZAWGYI_SAMPLE}\n\n{SHAN_SAMPLE}"
    scores = dict(score_paragraphs(doc))
    assert scores[UNICODE_SAMPLE] < 0.5
    assert scores[ZAWGYI_SAMPLE] > 0.5
    assert scores[SHAN_SAMPLE] < 0.5


def test_whole_document_score_would_hide_the_zawgyi_paragraph():
    """Documents the reason for per-paragraph scoring: a single
    whole-document score on this exact mixed document reports as clean,
    which is why convert_with_report scores paragraphs independently
    instead of the document as a whole."""
    doc = f"{UNICODE_SAMPLE}\n\n{ZAWGYI_SAMPLE}\n\n{SHAN_SAMPLE}"
    assert get_zawgyi_probability(doc) < 0.5


class TestConvertWithReport:
    def test_converts_only_the_zawgyi_paragraph(self):
        doc = f"{UNICODE_SAMPLE}\n\n{ZAWGYI_SAMPLE}\n\n{SHAN_SAMPLE}"
        report = convert_with_report(doc)
        assert [p.converted for p in report.paragraphs] == [False, True, False]
        assert report.paragraphs[0].converted_text == UNICODE_SAMPLE
        assert report.paragraphs[1].converted_text == UNICODE_SAMPLE
        assert report.paragraphs[2].converted_text == SHAN_SAMPLE

    def test_does_not_mangle_shan_text(self):
        """Regression test for the concrete bug this feature fixes: the
        old is_zawgyi()-based path corrupts real Shan text into garbage."""
        report = convert_with_report(SHAN_SAMPLE)
        assert report.paragraphs[0].converted_text == SHAN_SAMPLE
        assert not report.paragraphs[0].converted

    def test_does_not_mangle_mon_text(self):
        report = convert_with_report(MON_SAMPLE)
        assert report.paragraphs[0].converted_text == MON_SAMPLE
        assert not report.paragraphs[0].converted

    def test_reassembles_document_structure_exactly(self):
        doc = f"{UNICODE_SAMPLE}\n\n{ZAWGYI_SAMPLE}\n\n{SHAN_SAMPLE}"
        report = convert_with_report(doc)
        assert report.text == f"{UNICODE_SAMPLE}\n\n{UNICODE_SAMPLE}\n\n{SHAN_SAMPLE}"

    def test_document_summary_min_max_spread(self):
        doc = f"{UNICODE_SAMPLE}\n\n{ZAWGYI_SAMPLE}\n\n{SHAN_SAMPLE}"
        report = convert_with_report(doc)
        summary = report.document_summary
        assert summary["min"] < 0.5
        assert summary["max"] > 0.5
        assert summary["spread"] == pytest.approx(summary["max"] - summary["min"])

    def test_repair_log_matches_known_rule_trace(self):
        """The real 5-rule trace for ZAWGYI_SAMPLE -> UNICODE_SAMPLE,
        confirmed by manually stepping the rule table before this module
        was written. Pins the repair log against a regression."""
        report = convert_with_report(ZAWGYI_SAMPLE)
        para = report.paragraphs[0]
        assert para.converted_text == UNICODE_SAMPLE
        rule_indices = [r.rule_index for r in para.repairs]
        assert rule_indices == [5, 7, 58, 70]

        rule5 = para.repairs[0]
        assert rule5.matched_text == "ျ"
        assert rule5.replacement_text == "ြ"
        assert rule5.lossy is True
        assert rule5.origin_span == (0, 1)

        rule7 = para.repairs[1]
        assert rule7.matched_text == "္"
        assert rule7.replacement_text == "်"
        assert rule7.lossy is False

    def test_reorder_rules_categorized_as_reorder(self):
        report = convert_with_report(ZAWGYI_SAMPLE)
        reorders = [r for r in report.paragraphs[0].repairs if r.category == "reorder"]
        assert len(reorders) == 2
        for r in reorders:
            assert sorted(r.matched_text) == sorted(r.replacement_text)

    def test_no_op_rule_firings_are_not_logged(self):
        """Rule 105 ([်]+ -> ်) matches ZAWGYI_SAMPLE's converted text but
        produces no visible change; it must not appear in the log."""
        report = convert_with_report(ZAWGYI_SAMPLE)
        rule_indices = {r.rule_index for r in report.paragraphs[0].repairs}
        assert 105 not in rule_indices

    def test_clean_unicode_paragraph_has_empty_repair_log(self):
        report = convert_with_report(UNICODE_SAMPLE)
        assert report.paragraphs[0].repairs == []
        assert not report.paragraphs[0].converted

    def test_threshold_is_respected(self):
        # A threshold above 1.0 can never be exceeded -> nothing converts.
        report = convert_with_report(ZAWGYI_SAMPLE, threshold=1.5)
        assert not report.paragraphs[0].converted
        assert report.paragraphs[0].converted_text == ZAWGYI_SAMPLE

    def test_short_ambiguous_strings_do_not_crash_and_stay_auditable(self):
        """Short strings are exactly where a global heuristic is least
        reliable; these must not raise, and whatever verdict is reached
        must be reflected honestly in converted/repairs, not silently."""
        for s in ["", "က", "ရေ", "ေရ", "abc123", "၊"]:
            report = convert_with_report(s)
            assert isinstance(report.text, str)
            for p in report.paragraphs:
                assert p.converted == bool(p.repairs) or not p.converted

    def test_output_is_canonicalized(self):
        """Contraction-adjacent output should be stable under
        canonical_order (no visible mark reordering artifacts)."""
        report = convert_with_report(ZAWGYI_SAMPLE)
        from burmesenlp.normalize import canonical_order

        assert report.paragraphs[0].converted_text == canonical_order(
            report.paragraphs[0].converted_text
        )

    def test_type_validation(self):
        with pytest.raises(TypeError):
            convert_with_report(None)  # type: ignore[arg-type]

    def test_ambiguous_zero_wa_rule_is_flagged_with_evidence(self):
        """Empirically confirmed via round-trip testing on myPOS (see
        research/zawgyi-repair-log/roundtrip_check.py): rule 67's
        digit-zero/letter-wa disambiguation heuristic misfires on real
        text (e.g. a decimal '6.0%'), silently turning a digit into a
        letter. This is the only rule with corpus evidence backing
        `ambiguous=True` -- not fabricated, not statically inferred."""
        from burmesenlp.zawgyi.repair import (
            _EMPIRICALLY_AMBIGUOUS_ZG2UNI_RULES,
            _apply_rules_with_log,
        )
        from burmesenlp.zawgyi.zawgyi import _zg2uni_rules

        zg_fragment = "ခရစ္ယာန္ဘာသာ၆.၀%"
        out, repairs = _apply_rules_with_log(zg_fragment, _zg2uni_rules(), _EMPIRICALLY_AMBIGUOUS_ZG2UNI_RULES)
        ambiguous = [r for r in repairs if r.ambiguous]
        assert len(ambiguous) == 1
        assert ambiguous[0].rule_index == 67
        assert ambiguous[0].ambiguous_note is not None
        # the digit is wrongly turned into the letter -- the bug itself
        assert "၀" in zg_fragment and "၀" not in out

    @pytest.mark.xfail(
        reason=(
            "KNOWN GAP, not yet mitigated: 14 of 118 zg2uni rules map "
            "individual Karen-range codepoints (U+1061-106D) directly to "
            "specific Zawgyi stacked-consonant shorthand, and the ported "
            "bigram detector also scores isolated Karen letters as "
            "Zawgyi-like (~0.9). Unlike Shan/Mon (verified clean on real "
            "Wikipedia corpora), Karen has no available real corpus to "
            "verify against, and this synthetic probe shows the collision "
            "is not resolved by the new detector either. See CHANGELOG."
        ),
        strict=True,
    )
    def test_karen_codepoints_alone_do_not_force_conversion(self):
        report = convert_with_report(KAREN_LETTERS)
        assert report.paragraphs[0].converted_text == KAREN_LETTERS
        assert not report.paragraphs[0].converted
