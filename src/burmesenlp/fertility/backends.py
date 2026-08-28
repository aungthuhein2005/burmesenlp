# -*- coding: utf-8 -*-
"""Tokenizer backends for the fertility profiler.

Requires the optional ``fertility`` extra (``pip install
burmesenlp[fertility]``): ``tiktoken`` + ``tokenizers``, both imported
lazily so the base install stays dependency-free. Deliberately NOT
``transformers`` -- ``tokenizers`` (HuggingFace's Rust tokenization
library) loads the same ``tokenizer.json`` vocab/merge files without the
ML framework, torch, or GPU deps around it.

Four tokenizers, chosen for what they let us claim:

  - ``cl100k_base`` (tiktoken) -- GPT-3.5-turbo / GPT-4 (original)
  - ``o200k_base`` (tiktoken) -- GPT-4o / GPT-4o-mini
  - ``qwen2.5`` (tokenizers, Qwen/Qwen2.5-0.5B) -- open, ungated, large
    multilingual vocab
  - ``mistral`` (tokenizers, mistralai/Mistral-7B-v0.1) -- open, ungated.
    Substituted for Gemma, which requires a gated/authenticated
    HuggingFace download (confirmed: HTTP 401 on tokenizer.json without
    auth) -- not worth the friction for a second open contrast point.

Two from the same vendor (OpenAI) is deliberate: the point is to show
fertility is a property of a tokenizer's vocabulary, not of the
language, and that claim needs an intra-vendor comparison, not just
vendor-vs-vendor.

Vocab/merge files are fetched at runtime and cached under
:func:`burmesenlp.models.cache.model_cache_dir`, never vendored --
Qwen's tokenizer.json alone is ~7MB, Mistral's is comparable, both far
past the 28KB precedent from the Zawgyi detector model.
"""
from __future__ import annotations

import urllib.request
from pathlib import Path
from typing import List, Protocol

from ..models.cache import model_cache_dir

_USER_AGENT = "burmesenlp-fertility/1.0"

_HF_TOKENIZER_URLS = {
    "qwen2.5": "https://huggingface.co/Qwen/Qwen2.5-0.5B/resolve/main/tokenizer.json",
    "mistral": "https://huggingface.co/mistralai/Mistral-7B-v0.1/resolve/main/tokenizer.json",
}

TOKENIZER_NAMES = ("cl100k_base", "o200k_base", "qwen2.5", "mistral")


class TokenizerBackend(Protocol):
    """Minimal interface the profiler needs from any tokenizer."""

    name: str

    def encode(self, text: str) -> List[int]: ...

    def token_byte_lengths(self, token_ids: "List[int]") -> "List[int]":
        """Byte length of each token's raw representation -- used to
        mechanically verify byte-fallback behavior (a token whose byte
        length is less than a full multi-byte character's encoding cannot
        be a real merge of that character)."""
        ...


def _cache_path(name: str) -> Path:
    d = model_cache_dir() / "fertility"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{name}.json"


def _download(url: str, dest: Path) -> Path:
    if dest.exists():
        return dest
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
        data = response.read()
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.write_bytes(data)
    tmp.rename(dest)
    return dest


class TiktokenBackend:
    """Wraps a tiktoken encoding (``cl100k_base`` / ``o200k_base``)."""

    def __init__(self, name: str) -> None:
        try:
            import tiktoken
        except ImportError as exc:  # pragma: no cover - exercised without extra
            raise ImportError(
                "the fertility profiler requires the optional extra: "
                "pip install burmesenlp[fertility]"
            ) from exc
        self.name = name
        self._enc = tiktoken.get_encoding(name)

    def encode(self, text: str) -> List[int]:
        return self._enc.encode(text)

    def token_byte_lengths(self, token_ids: "List[int]") -> "List[int]":
        return [len(self._enc.decode_single_token_bytes(t)) for t in token_ids]


class HFTokenizersBackend:
    """Wraps a ``tokenizers.Tokenizer`` loaded from a downloaded
    ``tokenizer.json`` (Qwen2.5 / Mistral).

    The two use genuinely different vocab conventions -- confirmed by
    inspecting the downloaded JSON, not assumed to match: Qwen2.5 is
    GPT-2-style byte-level BPE (``decoder.type == "ByteLevel"``), where
    each vocab piece is a printable-Unicode remapping of raw bytes and a
    piece's character count IS its byte length by construction. Mistral
    uses a literal-Unicode (SentencePiece-derived, ``Metaspace``) vocab,
    where pieces are the actual characters and byte length requires
    UTF-8-encoding the piece text. Getting this wrong would corrupt any
    byte-fallback check run against the wrong backend, so the scheme is
    detected per tokenizer rather than assumed uniform.
    """

    def __init__(self, name: str) -> None:
        try:
            from tokenizers import Tokenizer
        except ImportError as exc:  # pragma: no cover - exercised without extra
            raise ImportError(
                "the fertility profiler requires the optional extra: "
                "pip install burmesenlp[fertility]"
            ) from exc
        if name not in _HF_TOKENIZER_URLS:
            raise ValueError(f"unknown tokenizer {name!r}; choose from {sorted(_HF_TOKENIZER_URLS)}")
        path = _download(_HF_TOKENIZER_URLS[name], _cache_path(name))
        self.name = name
        self._tok = Tokenizer.from_file(str(path))
        import json as _json

        with open(path, encoding="utf-8") as f:
            raw = _json.load(f)
        self._byte_level = (raw.get("decoder") or {}).get("type") == "ByteLevel"

    def encode(self, text: str) -> List[int]:
        return self._tok.encode(text, add_special_tokens=False).ids

    def token_byte_lengths(self, token_ids: "List[int]") -> "List[int]":
        out = []
        for t in token_ids:
            piece = self._tok.id_to_token(t) or ""
            if self._byte_level:
                out.append(len(piece))
            else:
                out.append(len(piece.replace("▁", " ").encode("utf-8")))
        return out


def load_backend(name: str) -> TokenizerBackend:
    if name in ("cl100k_base", "o200k_base"):
        return TiktokenBackend(name)
    if name in _HF_TOKENIZER_URLS:
        return HFTokenizersBackend(name)
    raise ValueError(f"unknown tokenizer {name!r}; choose from {TOKENIZER_NAMES}")


__all__ = ["TokenizerBackend", "TiktokenBackend", "HFTokenizersBackend", "load_backend", "TOKENIZER_NAMES"]
