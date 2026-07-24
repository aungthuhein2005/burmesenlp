# Project structure

```
burmesenlp/
├── pyproject.toml
├── mkdocs.yml                   # Documentation site (MkDocs Material)
├── README.md
├── STRUCTURE.md
├── LICENSE
├── CHANGELOG.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── .github/workflows/
│   ├── ci.yml
│   └── docs.yml                 # Build + deploy GitHub Pages
│
├── docs/                        # Documentation source
│   ├── index.md
│   ├── getting-started/
│   ├── user-guide/
│   ├── algorithms/
│   ├── tutorials/
│   ├── api/
│   ├── developer-guide/
│   ├── research/
│   └── assets/
│
├── src/
│   └── burmesenlp/
│       ├── __init__.py              # Public API (BurmeseNLP, process, tokenize helpers)
│       ├── __main__.py
│       ├── py.typed
│       │
│       ├── cli/                     # Console script
│       ├── pipeline/                # BurmeseNLP facade + process() → Document
│       ├── normalize/               # NFC / zero-width / Zawgyi heuristic
│       ├── zawgyi/                  # Zawgyi <-> Unicode conversion (+ rule JSON)
│       ├── grammar/                 # Closed-class lists (in code)
│       ├── lexicon/                 # Word → POS dictionary (+ data/*.json)
│       │
│       ├── tokenize/                # Tokenization (engine-dispatched)
│       │   ├── engine.py
│       │   ├── syllable.py
│       │   ├── word.py
│       │   ├── sentence.py
│       │   └── longest.py
│       │
│       ├── tag/                     # POS tagging (engine-dispatched)
│       │   ├── engine.py
│       │   ├── candidates.py
│       │   ├── disambiguator.py
│       │   ├── rule.py
│       │   └── rules/
│       │
│       ├── chunking/                # Shallow phrase chunking (YAML-driven)
│       │   ├── models.py            # Chunk, ChunkType
│       │   ├── matcher.py           # Pattern DSL compiler/matcher
│       │   ├── rules.py             # YAML loader / CompiledGrammar
│       │   ├── chunker.py           # PhraseChunker, chunk()
│       │   ├── noun.py / verb.py / clause.py
│       │   └── __init__.py
│       │
│       ├── mwe/                     # BMWE multi-word expression merge
│       │   ├── models.py            # MWEEntry, MWEToken
│       │   ├── trie.py              # Token-sequence trie
│       │   ├── loader.py            # JSON/TXT → same word tokenizer as pipeline
│       │   ├── matcher.py           # Priority / longest choose
│       │   ├── validator.py         # V1 AcceptAllValidator
│       │   ├── engine.py            # BMWEEngine
│       │   └── __init__.py
│       │
│       ├── models/                  # v2+ model hooks (stubs only)
│       ├── corpus/
│       │   ├── idioms/              # idioms.json (+ idioms.cache.json)
│       │   └── grammar/             # V1 chunking YAML
│       │       ├── phrase_rules.yml
│       │       ├── phrase_markers.yml
│       │       └── phrase_exceptions.yml
│       │
│       └── (compat shims)
│           ├── syllables/ → tokenize.syllable
│           ├── words/     → tokenize.longest
│           ├── sentences/ → tokenize.sentence
│           └── postag/    → tag.rule
│
└── tests/
```

## Roadmap fit

| Version | Focus | Where it plugs in |
| --- | --- | --- |
| v1 (now) | Rule-based | `tokenize` (`longest`), `mwe` (BMWE), `tag` (`rule`), `chunking` (YAML) |
| v2 | Hybrid + statistical | New engines in `tokenize.engine` / `tag.engine`; artifacts via `models/` |
| v3 | Deep learning | Transformer backends registered the same way |
| v4 | Research / EvoPiece | Tokenizer engine + benchmark tooling |

## Data flow

```
raw text
  → normalize
  → tokenize.syllable
  → tokenize.word (engine="longest")
  → mwe (BMWEEngine: trie merge; loader uses the same word tokenizer)
  → tag (engine="rule") on merged words
       1. candidates.py
       2. context rules
       3. grammar rules
       4. TAG_PREFERENCE fallback
  → chunking (YAML patterns: NP / VP / PP / CLAUSE)
  → sentence segmentation (grammar-aware over phrase chunks)
  → Document (words post-MWE, mwe spans, pos_tags, chunks, sentences, …)
```

`process(text)` and `BurmeseNLP.process` run this once with shared word tokens.

V1 loads `corpus/idioms/idioms.json` (via `idioms.cache.json` when fresh) for
BMWE and `corpus/grammar/*.yml` for phrase chunking. Other `corpus/` trees
(NER, sentiment, embeddings, …) remain placeholders for later versions.
