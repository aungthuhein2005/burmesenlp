# BurmeseNLP

**BurmeseNLP** (`burmesenlp`) is an open-source Python library for rule-based
Myanmar (Burmese) natural language processing.

Version **1.0** focuses on preprocessing: normalization, Zawgyi ↔ Unicode
**APIs**, syllable / word / sentence segmentation, multi-word expressions
(BMWE), lexicon management, rule-based POS tagging, and phrase chunking.
It is fast, dependency-light, and designed as the foundation for future
hybrid and machine-learning engines.

```bash
pip install burmesenlp
```

**Docs:** [https://aungthuhein2005.github.io/burmesenlp/](https://aungthuhein2005.github.io/burmesenlp/)
(source in [`docs/`](docs/); build with `pip install -e ".[docs]" && mkdocs serve`)

```python
from burmesenlp import process

doc = process("ကျွန်တော်ကျောင်းသို့သွားသည်။")
print(doc["words"])
# ['ကျွန်တော်', 'ကျောင်း', 'သို့', 'သွား', 'သည်', '။']
```

No dictionary path or model download is required.

## Features

- **Normalization** — strip zero-width characters, Unicode NFC
- **Zawgyi ↔ Unicode** — conversion rules plus a heuristic detector
- **Syllable tokenization** — sylbreak-style boundaries
- **Word segmentation** — dictionary longest-match (`engine="longest"`)
- **Sentence segmentation** — grammar-aware (after POS + phrase chunks)
- **Multi-word expressions** — BMWE trie merge (idioms)
- **Lexicon** — bundled tagged vocabulary (~24k entries) + mergeable custom JSON/txt
- **POS tagging** — rule / lexicon-based (`engine="rule"`)
- **Phrase chunking** — YAML-driven NP / VP / PP / …
- **Pipeline API** — `process(text)` and stateful `BurmeseNLP`
- **CLI** — `burmesenlp` console script



## Installation

```bash
pip install burmesenlp
```

From a clone (development):

```bash
pip install -e ".[dev]"
```

Requires **Python 3.9+**. Runtime depends on **PyYAML** (phrase grammar); there
are no other third-party NLP dependencies.

## Quick start

```python
from burmesenlp import BurmeseNLP, process, word_tokenize, pos_tag, zg2uni
import json

# One-shot pipeline (returns a Document)
doc = process("စာပေကိုဖတ်သည်။သူကစားသည်။")
doc.words
doc.sentences
doc.pos_tags
doc.chunks

# JSON export
json.dumps(doc.to_dict(), ensure_ascii=False, indent=2)

# Stateful pipeline
nlp = BurmeseNLP()
nlp.syllable_segment("မြန်မာစာပေ")
nlp.word_segment("ကျွန်တော်ကျောင်းသို့သွားသည်")
nlp.sentence_segment("စာပေကိုဖတ်သည်။သူကစားသည်။")
nlp.pos_tag(["ကျွန်တော်", "ကျောင်း", "သို့", "သွား", "သည်"])

# Helpers
word_tokenize("ကျွန်တော်ကျောင်းသို့သွားသည်", engine="longest")
pos_tag(["ကျွန်တော်", "ကျောင်း"], engine="rule")
zg2uni("ျမန္မာစာေပ")
```



### Custom dictionary

`BurmeseNLP()` loads bundled `lexicon/data/*.json` merged with closed-class
seed lists. Extra files **merge** onto that default (per-word tag union).
Missing or malformed files raise `LexiconError` — there is no silent fallback.

```python
nlp = BurmeseNLP(dictionary_path="my_dict.json")  # or .txt import
nlp.add_to_dictionary("နည်းပညာ", ["NOUN"])
nlp.save_dictionary("my_dict.json")               # atomic JSON write
```

**Canonical JSON:** `{ "word": ["tag1", "tag2"] }`

**Import** `.txt`**:** `word<TAB>tag1,tag2`

Tags must be from `burmesenlp.POS_TAGS`. To load a file *instead of* the
bundled default, use `BurmeseNLP(lexicon=Lexicon.from_file(path))`.

### CLI

```bash
burmesenlp --mode words "ကျွန်တော်ကျောင်းသို့သွားသည်။"
burmesenlp --json --mode process "စာပေကိုဖတ်သည်။"
burmesenlp --mode zg2uni "ျမန္မာစာေပ"
```



## Module overview


| Module      | Role                                 |
| ----------- | ------------------------------------ |
| `pipeline`  | `BurmeseNLP`, `process()`, `Document` |
| `normalize` | NFC / zero-width / Zawgyi heuristic  |
| `zawgyi`    | `uni2zg` / `zg2uni` / `to_unicode`   |
| `tokenize`  | syllable, word (`longest`), sentences |
| `mwe`       | BMWE multi-word expression merge     |
| `tag`       | rule-based POS                       |
| `chunking`  | phrase chunks (YAML grammar)         |
| `lexicon`   | dictionary load / merge / save       |
| `grammar`   | closed-class lists                   |
| `cli`       | console entry point                  |


See [STRUCTURE.md](STRUCTURE.md) for the full layout and the
[documentation site](https://aungthuhein2005.github.io/burmesenlp/) for guides
and API reference. Corpus trees under `corpus/` hold V1 grammar/idioms plus
scaffolds for later versions.

## Current limitations

Version 1 is **rule-based only**:

- No machine learning, Transformers, CRF, or embeddings
- No SentencePiece / BPE / EvoPiece tokenizers
- No NER, sentiment, or spell checking
- Word segmentation quality depends on lexicon coverage; longest-match may
prefer compounds present in the dictionary
- POS and chunk rules are heuristic — expect residual tagging/chunk errors
- Zawgyi *detection* is heuristic — prefer explicit `zg2uni` when encoding
is known
- **`process()` does not auto-convert Zawgyi.** It only runs `normalize()`
  (NFC / zero-width). Convert first:

```python
from burmesenlp import zg2uni, process

doc = process(zg2uni(zawgyi_text))
```

These gaps are intentional for a lightweight, deterministic V1.

## Roadmap


| Version | Focus                                                         |
| ------- | ------------------------------------------------------------- |
| **1.x** | Rule-based production toolkit (this release)                  |
| **2.x** | Hybrid NLP (rules + statistical models) via engine registries |
| **3.x** | Deep learning backends                                        |
| **4.x** | Research platform (e.g. EvoPiece, benchmarks)                 |




## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md),
and [SECURITY.md](SECURITY.md).
Please keep V1 PRs focused on rule-based quality, packaging, docs, and tests —
do not add unfinished ML features to the public API.

## License

Apache-2.0 — see [LICENSE](LICENSE).

## References

- Ye Kyaw Thu et al., myPOS / sylbreak conventions for Myanmar NLP
- Rabbit Converter–style Zawgyi ↔ Unicode rule tables

