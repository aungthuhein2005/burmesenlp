# Project structure

```
burmesenlp/
├── pyproject.toml
├── README.md
├── STRUCTURE.md
├── .gitignore
│
├── src/
│   └── burmesenlp/
│       ├── __init__.py              # Public API (BurmeseNLP, process, tokenize helpers)
│       ├── __main__.py
│       ├── py.typed
│       │
│       ├── cli/                     # Console script
│       ├── pipeline/                # BurmeseNLP facade + process()
│       ├── normalize/               # NFC / zero-width / Zawgyi heuristic
│       ├── zawgyi/                  # Zawgyi <-> Unicode conversion
│       ├── grammar/                 # Closed-class lists
│       ├── lexicon/                 # Word → POS dictionary
│       │
│       ├── tokenize/                # Tokenization (engine-dispatched)
│       │   ├── engine.py            # word engine registry (longest today)
│       │   ├── syllable.py
│       │   ├── word.py
│       │   ├── sentence.py
│       │   └── longest.py           # greedy dictionary match
│       │
│       ├── tag/                     # POS tagging (engine-dispatched)
│       │   ├── engine.py            # tagger registry (rule today)
│       │   └── rule.py
│       │
│       ├── models/                  # v2+ model architecture (stubs only)
│       │   ├── loader.py
│       │   ├── registry.py
│       │   └── cache.py
│       │
│       ├── corpus/                  # Linguistic resources (not ML weights)
│       │   ├── dictionaries/
│       │   ├── names/
│       │   ├── syllables/
│       │   ├── normalization/
│       │   ├── tokenizer/           # vocab JSON only
│       │   ├── pos/
│       │   ├── ner/
│       │   ├── sentiment/
│       │   ├── spell/
│       │   └── metadata/
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
| v1 (now) | Rule-based | `tokenize` (`longest`), `tag` (`rule`) |
| v2 | Hybrid + statistical | New engines in `tokenize.engine` / `tag.engine`; artifacts via `models/` |
| v3 | Deep learning | Transformer backends registered the same way |
| v4 | Research / EvoPiece | Tokenizer engine + benchmark tooling; vocab stays in `corpus/` |

## Data flow

```
raw text
  → normalize
  → tokenize.syllable
  → tokenize.word (engine="longest")
  → tokenize.sentence
  → tag (engine="rule")
```

`process(text)` and `BurmeseNLP.process` run this once with shared word tokens.
