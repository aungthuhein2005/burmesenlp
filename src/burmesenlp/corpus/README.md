# Corpus resources

This package directory holds **linguistic resource files** and a small
loader/registry API.

## Production (V1) — used by the public pipeline

| Resource | Location | Used by |
| --- | --- | --- |
| Tagged lexicon | `burmesenlp/lexicon/data/*.json` | word segment, POS |
| Phrase / clause grammar | `corpus/grammar/*.yml` | phrase + typed clause chunking |
| Idioms | `corpus/idioms/idioms.json` (+ cache) | BMWE |
| Zawgyi rules | `burmesenlp/zawgyi/*.json` | `zg2uni` / `uni2zg` |
| Closed-class lists | `burmesenlp/grammar` (code) | POS / sentences |

## Lookup resources (V1 API, not in `process()`)

| Resource | Location | Used by |
| --- | --- | --- |
| Gazetteers | `corpus/gazetteers/` | `GazetteerManager` |

See [gazetteers/README.md](gazetteers/README.md). Load via
`GazetteerManager()` for contains/lookup/longest_match. Entity type comes
from the filename; data stay compact string arrays (except holidays).

See [metadata/corpus.json](metadata/corpus.json) for machine-readable inventory
(license, version, role).

Idiom file format: [idioms/README.md](idioms/README.md) (JSON **string array**,
category from path — not `{text, type}` objects).

Phrase grammar:

- `phrase_rules.yml` — NP / VP / PP / ADJP / NUMP / FIXED_EXPRESSION
- `clause_rules.yml` — settings, reusable phrase templates, clause kinds (inherit / relation / markers)
- `semantic_roles.yml` — default PP semantic roles (V1 heuristics; prefer over legacy `postposition_roles.yml`)
- `phrase_markers.yml` — boundary markers
- `phrase_exceptions.yml` — greetings / never-split / specials

## Placeholders (not V1 features)

Directories such as `ner/`, `sentiment/`, `names/`, `dictionaries/`,
`syllables/`, and related stub files are **scaffolds for later versions**.
They are **not** loaded by `BurmeseNLP.process()` and must not be documented
as working V1 capabilities.

## Later versions

Hybrid / ML engines may load resources from here (or via `burmesenlp.models`).
Until then, treat unfinished trees as reserved layout only.
