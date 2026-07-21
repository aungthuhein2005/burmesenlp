import json

import pytest

from burmesenlp.lexicon import Lexicon, LexiconError


def test_default_lexicon_builds():
    lex = Lexicon.default()
    assert len(lex) > 100
    assert "မြန်မာ" in lex


def test_multi_tag_words_accumulate_and_order_by_preference():
    lex = Lexicon.default()
    # သူ is both noun and pronoun; pron ranks before n in TAG_PREFERENCE.
    assert lex.tags("သူ") == ("pron", "n")
    # ၏ is both ppm (possessive) and part (final particle).
    assert lex.tags("၏") == ("ppm", "part")


def test_json_roundtrip(tmp_path):
    lex = Lexicon.default()
    path = tmp_path / "dict.json"
    lex.save(str(path))
    reloaded = Lexicon.from_json(str(path))
    assert len(reloaded) == len(lex)
    assert reloaded.tags("မြန်မာ") == lex.tags("မြန်မာ")


def test_missing_file_raises_instead_of_silent_fallback(tmp_path):
    with pytest.raises(LexiconError):
        Lexicon.from_json(str(tmp_path / "does_not_exist.json"))


def test_invalid_json_raises(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(LexiconError):
        Lexicon.from_json(str(path))


def test_schema_violations_raise(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")
    with pytest.raises(LexiconError):
        Lexicon.from_json(str(path))

    with pytest.raises(LexiconError):
        Lexicon({"word": "n"})  # tags must be a list, not a string
    with pytest.raises(LexiconError):
        Lexicon({"word": ["nope"]})  # unknown tag
    with pytest.raises(LexiconError):
        Lexicon({"": ["n"]})  # empty word
    with pytest.raises(LexiconError):
        Lexicon({"two words": ["n"]})  # whitespace in word


def test_add_merges_tags_and_updates_longest_match():
    lex = Lexicon.default()
    lex.add("နည်းပညာ", ["n"])
    assert "နည်းပညာ" in lex
    lex.add("နည်းပညာ", ["fw"])
    assert set(lex.tags("နည်းပညာ")) == {"n", "fw"}
    assert lex.max_word_syllables >= 3


def test_from_file_merge_default_keeps_seed_and_unions_tags(tmp_path):
    path = tmp_path / "domain.json"
    path.write_text(
        json.dumps({"နည်းပညာ": ["n"], "သူ": ["fw"]}, ensure_ascii=False),
        encoding="utf-8",
    )
    lex = Lexicon.from_file(str(path), merge_default=True)
    assert "နည်းပညာ" in lex
    # Seed function words survive a domain-only overlay.
    assert "ရှိ" in lex
    assert "ကျွန်တော်" in lex
    assert "ကို" in lex
    # Overlapping word unions tags rather than overwriting.
    assert set(lex.tags("သူ")) == {"pron", "n", "fw"}


def test_from_file_without_merge_is_file_only(tmp_path):
    path = tmp_path / "tiny.json"
    path.write_text(json.dumps({"နည်းပညာ": ["n"]}, ensure_ascii=False), encoding="utf-8")
    lex = Lexicon.from_file(str(path), merge_default=False)
    assert list(lex.words()) == ["နည်းပညာ"]
    assert "ရှိ" not in lex


def test_txt_import_format(tmp_path):
    path = tmp_path / "words.txt"
    path.write_text(
        "# domain vocabulary\n"
        "နည်းပညာ\tn\n"
        "သူ\tfw\n"
        "\n"
        "ဒေတာ\tn,fw\n",
        encoding="utf-8",
    )
    lex = Lexicon.from_txt(str(path), merge_default=True)
    assert lex.tags("နည်းပညာ") == ("n",)
    assert set(lex.tags("သူ")) == {"pron", "n", "fw"}
    assert set(lex.tags("ဒေတာ")) == {"n", "fw"}
    assert "ရှိ" in lex  # seed preserved


def test_txt_import_malformed_raises(tmp_path):
    path = tmp_path / "bad.txt"
    path.write_text("no-tab-here n\n", encoding="utf-8")
    with pytest.raises(LexiconError, match="expected"):
        Lexicon.from_txt(str(path))

    path.write_text("word\t\n", encoding="utf-8")
    with pytest.raises(LexiconError, match="no POS tags"):
        Lexicon.from_txt(str(path))


def test_unsupported_extension_raises(tmp_path):
    path = tmp_path / "dict.csv"
    path.write_text("x,n\n", encoding="utf-8")
    with pytest.raises(LexiconError, match="unsupported dictionary format"):
        Lexicon.from_file(str(path))


def test_save_always_writes_json_even_after_txt_import(tmp_path):
    src = tmp_path / "in.txt"
    src.write_text("နည်းပညာ\tn\n", encoding="utf-8")
    lex = Lexicon.from_txt(str(src))
    out = tmp_path / "out.json"
    lex.save(str(out))
    assert json.loads(out.read_text(encoding="utf-8")) == {"နည်းပညာ": ["n"]}
