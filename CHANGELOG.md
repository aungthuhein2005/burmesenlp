# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Keep `__version__` in `src/burmesenlp/__init__.py`, the `version` field in
`pyproject.toml`, and this file in sync on every release.

## [1.0.0] - 2026-07-22

### Added

- Public rule-based Myanmar NLP toolkit: normalize, Zawgyi ↔ Unicode,
  syllable / word / sentence segmentation, lexicon, rule-based POS tagging.
- Bundled tagged default lexicon (`lexicon/data/*.json`) loaded automatically
  by `BurmeseNLP()` / `process()` with no `dictionary_path` required.
- High-level `process()` pipeline and `burmesenlp` CLI.
- Golden regression tests and packaging smoke checks for zero-config use.
- MIT license, contributing guide, code of conduct, and GitHub Actions CI
  (pytest, ruff, mypy).

### Notes

- Version 1 is **rule-based only**. It does not include machine learning,
  Transformers, CRF, SentencePiece, embeddings, NER, sentiment, or spell
  checking. Those belong in later roadmap versions.
