"""engine="xlmr" registration, import guard, and (opt-in) real-model tagging."""

from __future__ import annotations

import os

import pytest

from burmesenlp.tag import available_tag_engines, get_tag_engine, pos_tag


def test_xlmr_registered():
    assert "xlmr" in available_tag_engines()
    assert get_tag_engine("xlmr") is not None


def test_xlmr_not_wired_into_pipeline_engine_dispatch():
    """The rule engine stays the only one the PhraseChunker/pipeline path assumes."""
    from burmesenlp.pipeline import BurmeseNLP

    nlp = BurmeseNLP(gazetteer=False)
    assert isinstance(nlp.pos_tag(["စာ"]), list)  # unaffected by xlmr registration


@pytest.mark.xlmr
@pytest.mark.skipif(
    os.environ.get("BURMESENLP_XLMR_TEST") != "1",
    reason="Set BURMESENLP_XLMR_TEST=1 to download and run the real HF model",
)
def test_xlmr_tags_real_model():
    pytest.importorskip("transformers")
    pytest.importorskip("torch")

    words = ["ကျွန်တော်", "ကျောင်း", "သို့", "သွား", "သည်", "။"]
    tags = pos_tag(words, engine="xlmr")

    assert [w for w, _ in tags] == words
    assert all(isinstance(t, str) and t for _, t in tags)


def test_xlmr_missing_extra_raises_clear_import_error(monkeypatch):
    """Without transformers installed, instantiating the engine fails clearly."""
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "transformers":
            raise ImportError("no module named transformers")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(ImportError, match="burmesenlp\\[xlmr\\]"):
        pos_tag(["စာ"], engine="xlmr")
