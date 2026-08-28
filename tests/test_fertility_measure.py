"""Tests for burmesenlp.fertility.measure, using a fake tokenizer backend
so these run without the [fertility] extra or network access. Real-
tokenizer behavior (byte-fallback verification, scheme detection) is
covered separately in tests/test_fertility_backends.py, gated behind
BURMESENLP_FERTILITY_TEST=1.
"""

import pytest

from burmesenlp.fertility.measure import (
    CAVEAT_BASELINE_COMPARABLE_NOT_PARALLEL,
    CAVEAT_PER_RUN_OVERSTATES_TOTAL,
    aggregate_distribution,
    measure_text,
)


class OneTokenPerCharBackend:
    """Fake backend: one token per character, deterministic and free."""

    name = "fake-one-per-char"

    def encode(self, text):
        return list(range(len(text)))

    def token_byte_lengths(self, token_ids):
        return [1] * len(token_ids)


UNICODE_SAMPLE = "မြန်မာနိုင်ငံ၏ GDP သည် 2024 ခုနှစ်တွင် ရာခိုင်နှုန်း 5% တိုးတက်ခဲ့သည်။"


def test_measure_text_denominators_are_all_reported():
    backends = {"fake": OneTokenPerCharBackend()}
    r = measure_text(UNICODE_SAMPLE, backends)
    d = r.denominators
    assert d.bytes_ > d.chars > 0
    assert d.syllables > 0
    assert d.words > 0
    assert "nopipe" in d.word_scheme


def test_measure_text_type_validation():
    with pytest.raises(TypeError):
        measure_text(None, {})  # type: ignore[arg-type]


def test_one_token_per_char_backend_matches_char_count():
    backends = {"fake": OneTokenPerCharBackend()}
    r = measure_text(UNICODE_SAMPLE, backends)
    assert r.whole_document_tokens["fake"] == r.denominators.chars


def test_ratios_tokens_per_char_is_one_for_fake_backend():
    backends = {"fake": OneTokenPerCharBackend()}
    r = measure_text(UNICODE_SAMPLE, backends)
    ratios = r.ratios("fake")
    assert ratios["tokens_per_char"] == pytest.approx(1.0)
    assert ratios["tokens_per_byte"] < 1.0  # bytes > chars for Myanmar text
    assert ratios["tokens_per_word"] > 1.0  # more chars than words


def test_per_script_runs_sum_can_exceed_or_equal_whole_document():
    backends = {"fake": OneTokenPerCharBackend()}
    r = measure_text(UNICODE_SAMPLE, backends)
    per_run_sum = sum(run.tokens_per_tokenizer["fake"] for run in r.per_script_runs)
    # one-token-per-char is boundary-insensitive, so these are equal here;
    # the invariant that matters is per_run can never be LESS than whole-doc.
    assert per_run_sum >= r.whole_document_tokens["fake"]


def test_caveats_are_attached_to_the_result_not_just_documented():
    backends = {"fake": OneTokenPerCharBackend()}
    r = measure_text(UNICODE_SAMPLE, backends)
    assert CAVEAT_PER_RUN_OVERSTATES_TOTAL in r.caveats
    assert CAVEAT_BASELINE_COMPARABLE_NOT_PARALLEL in r.caveats


def test_canonicalize_default_true_is_a_noop_on_already_canonical_text():
    backends = {"fake": OneTokenPerCharBackend()}
    r = measure_text(UNICODE_SAMPLE, backends)
    assert r.canonicalized is True
    assert r.text == UNICODE_SAMPLE  # already canonical, per session's own check


def test_no_canonicalize_flag_is_respected():
    backends = {"fake": OneTokenPerCharBackend()}
    r = measure_text(UNICODE_SAMPLE, backends, canonicalize=False)
    assert r.canonicalized is False


def test_aggregate_distribution_reports_percentiles_not_just_mean():
    backends = {"fake": OneTokenPerCharBackend()}
    texts = ["က", "ကက", "ကကက", "ကကကက", "ကကကကက"]
    results = [measure_text(t, backends) for t in texts]
    dist = aggregate_distribution(results, "fake", "tokens_per_char")
    assert dist["n"] == 5
    assert dist["min"] <= dist["p10"] <= dist["p25"] <= dist["median"] <= dist["p75"] <= dist["p90"] <= dist["max"]
    assert dist["spread"] == pytest.approx(dist["max"] - dist["min"])


def test_aggregate_distribution_empty_input():
    dist = aggregate_distribution([], "fake", "tokens_per_char")
    assert dist["n"] == 0
    assert dist["mean"] is None


def test_a_document_far_worse_than_average_is_visible_in_max_not_hidden_by_mean():
    """The whole point of reporting distribution instead of mean: one bad
    document should show up in max/p90, not get averaged away."""

    class VariableBackend:
        name = "variable"

        def encode(self, text):
            # simulate one particular string being pathologically expensive
            if text == "PATHOLOGICAL":
                return list(range(100))
            return list(range(len(text)))

        def token_byte_lengths(self, token_ids):
            return [1] * len(token_ids)

    backends = {"v": VariableBackend()}
    texts = ["short", "short", "short", "short", "PATHOLOGICAL"]
    results = [measure_text(t, backends) for t in texts]
    dist = aggregate_distribution(results, "v", "tokens_per_char")
    assert dist["max"] > dist["mean"] * 2  # the outlier is visible
    assert dist["median"] < dist["mean"]  # mean is pulled up by the outlier
