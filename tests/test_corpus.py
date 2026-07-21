"""Tests for the corpus resource package scaffold."""

from burmesenlp.corpus import (
    cache_dir,
    list_resources,
    load_json,
    load_lines,
    resource_info,
    resource_path,
)
from burmesenlp.corpus.loader import CorpusError
from burmesenlp.corpus.registry import corpus_root

import pytest


def test_list_resources_includes_bundled_entries():
    names = list_resources()
    assert "dictionaries/words" in names
    assert "pos/tagset" in names
    assert "metadata/corpus" in names
    assert len(names) >= 20


def test_resource_path_and_info():
    info = resource_info("dictionaries/stopwords")
    assert info is not None
    assert info["bundled"] is True
    path = resource_path("dictionaries/stopwords")
    assert path.is_file()
    assert path.parent == corpus_root() / "dictionaries"


def test_load_lines_skips_comments(tmp_path, monkeypatch):
    # Point at a tiny fixture so this does not depend on dictionary size.
    sample = tmp_path / "sample.txt"
    sample.write_text("# comment\n\nhello\n# skip\nworld\n", encoding="utf-8")
    monkeypatch.setattr(
        "burmesenlp.corpus.loader.resource_path",
        lambda _name: sample,
    )
    assert load_lines("ignored") == ["hello", "world"]


def test_load_json_metadata():
    meta = load_json("metadata/corpus")
    assert meta["name"] == "burmesenlp-corpus"
    assert isinstance(meta["resources"], list)


def test_missing_resource_raises():
    with pytest.raises(CorpusError):
        resource_path("does/not/exist.txt")


def test_cache_dir_created(tmp_path, monkeypatch):
    monkeypatch.setenv("BURMESENLP_CACHE", str(tmp_path / "cache"))
    root = cache_dir()
    assert root.is_dir()
    assert root == tmp_path / "cache"
