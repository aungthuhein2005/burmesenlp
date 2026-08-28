"""Tests for burmesenlp.fertility.script (no third-party dependency)."""

from burmesenlp.fertility.script import segment_script_runs


def test_empty_string():
    assert segment_script_runs("") == []


def test_pure_myanmar_is_one_run():
    runs = segment_script_runs("မြန်မာစာပေ")
    assert len(runs) == 1
    assert runs[0].script == "myanmar"
    assert runs[0].text == "မြန်မာစာပေ"


def test_mixed_myanmar_latin_digit():
    text = "မြန်မာနိုင်ငံ၏ GDP သည် 2024 ခုနှစ်"
    runs = segment_script_runs(text)
    scripts = [r.script for r in runs]
    assert "myanmar" in scripts
    assert "latin" in scripts
    assert "digit" in scripts
    # reassembly must be exact
    assert "".join(r.text for r in runs) == text


def test_leading_space_attaches_to_following_run():
    """' GDP' should be part of the latin run, not a standalone whitespace
    run -- matches how BPE tokenizers actually spend a token on it."""
    text = "ကက GDP ခခ"
    runs = segment_script_runs(text)
    latin_runs = [r for r in runs if r.script == "latin"]
    assert len(latin_runs) == 1
    assert latin_runs[0].text == " GDP"


def test_trailing_whitespace_is_its_own_run():
    text = "ကက  "
    runs = segment_script_runs(text)
    assert runs[-1].script == "whitespace"
    assert runs[-1].text == "  "


def test_myanmar_digits_are_digit_not_myanmar():
    text = "၁၂၃"
    runs = segment_script_runs(text)
    assert len(runs) == 1
    assert runs[0].script == "digit"


def test_ascii_digits_are_digit():
    runs = segment_script_runs("123")
    assert len(runs) == 1
    assert runs[0].script == "digit"


def test_myanmar_punctuation_is_punctuation():
    runs = segment_script_runs("သည်။")
    assert runs[-1].script == "punctuation"
    assert runs[-1].text == "။"


def test_percent_sign_is_punctuation():
    runs = segment_script_runs("5%")
    scripts = [r.script for r in runs]
    assert scripts == ["digit", "punctuation"]


def test_runs_cover_the_whole_string_exactly():
    text = "မြန်မာနိုင်ငံ၏ GDP သည် 2024 ခုနှစ်တွင် ရာခိုင်နှုန်း 5% တိုးတက်ခဲ့သည်။"
    runs = segment_script_runs(text)
    assert "".join(r.text for r in runs) == text
    # spans must be contiguous and non-overlapping
    for prev, cur in zip(runs, runs[1:]):
        assert prev.end == cur.start
    assert runs[0].start == 0
    assert runs[-1].end == len(text)
