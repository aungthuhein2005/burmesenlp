"""Tests that the fertility backends fail gracefully when the optional
[fertility] extra is not importable. Deliberately NOT gated behind
BURMESENLP_FERTILITY_TEST -- this is exactly the path that matters most
when the extra is absent, so it must run in the default environment.
"""

import builtins

import pytest


def test_missing_extra_raises_helpful_import_error(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name in ("tiktoken", "tokenizers"):
            raise ImportError(f"No module named {name!r}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    from burmesenlp.fertility.backends import load_backend

    with pytest.raises(ImportError, match=r"burmesenlp\[fertility\]"):
        load_backend("cl100k_base")
    with pytest.raises(ImportError, match=r"burmesenlp\[fertility\]"):
        load_backend("qwen2.5")


def test_unknown_tokenizer_name_raises_value_error():
    from burmesenlp.fertility.backends import load_backend

    with pytest.raises(ValueError):
        load_backend("not-a-real-tokenizer")
