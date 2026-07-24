# Corpus resources (scaffold)

This package directory holds **linguistic resource files** and a small
loader/registry API.  It is an architectural scaffold for later versions.

## Version 1 (current)

Production NLP uses:

- `burmesenlp.lexicon` — bundled tagged lexicon (`lexicon/data/*.json`)
- `burmesenlp.zawgyi` — Zawgyi ↔ Unicode conversion rules
- `burmesenlp.grammar` — closed-class lists in code
- `burmesenlp.normalize` — NFC / zero-width handling in code
- `burmesenlp.corpus.grammar` — phrase-chunking YAML:
  - `phrase_rules.yml` — NP / VP / PP / ADJP / NUMP / CLAUSE patterns
  - `phrase_markers.yml` — boundary markers (case, SFP, conjunctions)
  - `phrase_exceptions.yml` — fixed expressions / never-split / specials
- `burmesenlp.corpus.idioms` — BMWE idiom list:
  - `idioms.json` — human-editable string list
  - `idioms.cache.json` — auto-generated tokenized cache (same word
    tokenizer as the pipeline; rebuilt when source or lexicon changes)

Directories such as `ner/`, `sentiment/`, `spell/`, `embeddings/`,
`tokenizer/`, and empty stub files under `names/` / `pos/` are
**placeholders**.  They are not features of the public V1 API and should
not be documented as working capabilities.

## Later versions

Hybrid / ML engines may load resources from here (or via `burmesenlp.models`).
Until then, treat unfinished trees as reserved layout only.
