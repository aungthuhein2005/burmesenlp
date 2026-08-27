# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Keep `__version__` in `src/burmesenlp/__init__.py`, the `version` field in
`pyproject.toml`, and this file in sync on every release.

## [1.1.0] - 2026-08-27

### Added

- `engine="xlmr"` POS tagger backed by
  [`aungthuhein-dev/burmese-pos-xlmr`](https://huggingface.co/aungthuhein-dev/burmese-pos-xlmr)
  (XLM-RoBERTa, myPOS tagset). Standalone tagging only, via
  `pos_tag(words, engine="xlmr")`; not wired into `BurmeseNLP.process()`.
  Requires the optional `xlmr` extra (`pip install burmesenlp[xlmr]`).

### Fixed

- Gazetteer entity spans are now locked to `PROPN` in `Document.pos_tags`
  itself, not just inside the phrase chunker. Multi-token names/places no
  longer keep garbage tags on trailing syllables from the context-blind
  first POS pass (e.g. `ထက်` as `CONJ`, `ဘို` as `VERB`).

## [1.0.1] - 2026-08-04

### Fixed

- Terminal vs non-terminal punctuation in sentence segmentation (`၊` no longer
  forces a hard sentence cut like `။`).
- Ambiguous NOUN/VERB stems before AUX (e.g. `ပညာသင်ခဲ့`) now tag as `VERB`.
- Lexicon entry for `ပညာသင်` includes `VERB` so context rules can apply.
- Removed invalid Trove classifier `Natural Language :: Burmese` (PyPI/TestPyPI
  rejected uploads with HTTP 400).
- Removed a zero-width-only junk key from bundled `default.json` (was logging
  on every import); lexicon sanitize skips are now debug-level only.

### Changed

- README / changelog / pipeline docs now describe gazetteer NER, clause
  parsing, and corpus export accurately (NER is list-based, not “absent”).

## [1.0.0] - 2026-07-24

### Added

- Public rule-based Myanmar NLP toolkit: normalize, Zawgyi ↔ Unicode APIs,
  syllable / word segmentation, lexicon, rule-based POS tagging.
- **BMWE** multi-word expression engine (token-sequence trie) with bundled
  `corpus/idioms/idioms.json` and optional `idioms.cache.json`.
- **Phrase chunking** (YAML grammar under `corpus/grammar/`).
- **Gazetteer NER** (list match after POS → `Document.entities`; entity spans
  locked as NP in the chunker).
- **Clause parsing** over phrases → `Document.sentence_trees` / `clauses`.
- **Corpus export** (`CorpusExporter` / `CorpusImporter`: JSONL, CoNLL, BRAT,
  Label Studio).
- **Grammar-aware sentence segmentation** after POS + chunks (no bare
  `သည်`/`တယ်` splits).
- Pipeline order: normalize → syllables → words → BMWE → POS → gazetteer →
  chunk → sentences → clauses → `Document`.
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
  Transformers, CRF, SentencePiece, embeddings, sentiment, or spell checking.
  NER in V1 is **gazetteer / list-based** (not statistical or neural).
- `process()` does **not** auto-convert Zawgyi; use `zg2uni` / `to_unicode`
  when the encoding is known or suspected.
