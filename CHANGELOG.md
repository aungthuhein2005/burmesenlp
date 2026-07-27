# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Keep `__version__` in `src/burmesenlp/__init__.py`, the `version` field in
`pyproject.toml`, and this file in sync on every release.

## [1.0.0] - 2026-07-24

### Added

- Public rule-based Myanmar NLP toolkit: normalize, Zawgyi ↔ Unicode APIs,
  syllable / word segmentation, lexicon, rule-based POS tagging.
- **BMWE** multi-word expression engine (token-sequence trie) with bundled
  `corpus/idioms/idioms.json` and optional `idioms.cache.json`.
- **Phrase chunking** (YAML grammar under `corpus/grammar/`).
- **Grammar-aware sentence segmentation** after POS + chunks (no bare
  `သည်`/`တယ်` splits).
- Pipeline order: normalize → syllables → words → BMWE → POS → chunk →
  sentences → `Document` (`words`, `pos_tags`, `chunks`, `mwe`, `sentences`,
  `to_dict()` / `to_json()`).
- POS tag `IDIOM` for merged MWEs; MWE-aware tagging.
- Bundled tagged default lexicon (`lexicon/data/*.json`) loaded automatically
  by `BurmeseNLP()` / `process()`.
- High-level `process()` / `BurmeseNLP` and `burmesenlp` CLI.
- MkDocs Material documentation (`docs/`, `mkdocs.yml`) and GitHub Pages
  workflow (`.github/workflows/docs.yml`).
- Golden regression tests, packaging smoke checks, and CI (pytest, ruff, mypy).
- Apache-2.0 license, contributing guide, code of conduct, and security policy.

### Notes

- Version 1 is **rule-based only**. It does not include machine learning,
  Transformers, CRF, SentencePiece, embeddings, NER, sentiment, or spell
  checking. Those belong in later roadmap versions.
- `process()` does **not** auto-convert Zawgyi; use `zg2uni` / `to_unicode`
  when the encoding is known or suspected.
