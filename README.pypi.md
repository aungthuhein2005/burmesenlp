# BurmeseNLP

Rule-based Myanmar (Burmese) NLP preprocessing: normalization, syllable / word /
sentence segmentation, POS tagging, phrase chunking, gazetteer NER, clause
parsing, and corpus export.

## Install

```bash
pip install burmesenlp
```

Requires **Python 3.9+**. Runtime depends on **PyYAML**.

No dictionary path or model download is required.

## Quick start

```python
from burmesenlp import (
    BurmeseNLP,
    CorpusExporter,
    process,
    word_tokenize,
    pos_tag,
    zg2uni,
)
import json

# One-shot pipeline (returns a Document)
doc = process("စာပေကိုဖတ်သည်။သူကစားသည်။")
doc.words
doc.sentences
doc.pos_tags
doc.chunks
doc.entities   # gazetteer NER (empty if no list hits)
doc.clauses    # clause layer over phrases

# Document JSON
json.dumps(doc.to_dict(), ensure_ascii=False, indent=2)
```

`Document` also supports dict-style access (`doc["words"]`).

## Gazetteer NER & clauses

```python
doc = process("ဒေါ်အောင်ဆန်းစုကြည် ရန်ကုန်ကို သွားသည်။")
for e in doc.entities:
    print(e.text, e.entity_type)

for clause in doc.clauses:
    print(clause.type, clause.text)

# Skip gazetteer matching
doc = process("...", gazetteer=False)
```

## Corpus export

```python
from burmesenlp import CorpusExporter, process

doc = process("စာပေကိုဖတ်သည်။")
exporter = CorpusExporter()
print(exporter.to_jsonl(doc))   # also CoNLL / BRAT / Label Studio
```

## Stateful pipeline

```python
from burmesenlp import BurmeseNLP

nlp = BurmeseNLP()
nlp.syllable_segment("မြန်မာစာပေ")
nlp.word_segment("ကျွန်တော်ကျောင်းသို့သွားသည်")
nlp.sentence_segment("စာပေကိုဖတ်သည်။သူကစားသည်။")
nlp.pos_tag(["ကျွန်တော်", "ကျောင်း", "သို့", "သွား", "သည်"])
```

## Helpers

```python
from burmesenlp import word_tokenize, pos_tag, zg2uni

word_tokenize("ကျွန်တော်ကျောင်းသို့သွားသည်", engine="longest")
pos_tag(["ကျွန်တော်", "ကျောင်း"], engine="rule")
zg2uni("ျမန္မာစာေပ")
```

## Custom dictionary

```python
from burmesenlp import BurmeseNLP

nlp = BurmeseNLP(dictionary_path="my_dict.json")  # or .txt import
nlp.add_to_dictionary("နည်းပညာ", ["NOUN"])
nlp.save_dictionary("my_dict.json")
```

Canonical JSON: `{ "word": ["tag1", "tag2"] }`. Tags must be from
`burmesenlp.POS_TAGS`.

## CLI

```bash
burmesenlp --mode words "ကျွန်တော်ကျောင်းသို့သွားသည်။"
burmesenlp --json --mode all "စာပေကိုဖတ်သည်။"
burmesenlp --mode zg2uni "ျမန္မာစာေပ"
```

