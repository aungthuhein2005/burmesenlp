# Quickstart

## One-shot pipeline

```python
from burmesenlp import process
import json

doc = process("မင်္ဂလာပါ။ ကျွန်တော်တို့သည် မြန်မာဘာသာစကားကို လေ့လာနေကြသည်။")

doc.words
doc.sentences
doc.pos_tags
doc.chunks
doc.mwe

# JSON-serializable dict
print(json.dumps(doc.to_dict(), ensure_ascii=False, indent=2))
```

!!! tip
    Always use `doc.to_dict()` or `doc.to_json()` before `json.dump`.
    A `Document` is not a plain dict.

## Stateful pipeline

```python
from burmesenlp import BurmeseNLP

nlp = BurmeseNLP()
nlp.word_segment("ကျွန်တော်ကျောင်းသို့သွားသည်")
nlp.sentence_segment("စာပေကိုဖတ်သည်။သူကစားသည်။")
nlp.pos_tag(["ကျွန်တော်", "ကျောင်း", "သို့", "သွား", "သည်"])
```

## Helpers

```python
from burmesenlp import word_tokenize, pos_tag, chunk, zg2uni

word_tokenize("ကျွန်တော်ကျောင်းသို့သွားသည်", engine="longest")
pos_tag(["ကျွန်တော်", "ကျောင်း"], engine="rule")
chunk("ကျွန်တော်ကျောင်းသို့သွားသည်။")
zg2uni("ျမန္မာစာေပ")
```

## Next

- [Pipeline & Document](../user-guide/pipeline.md)
- [Multi-word expressions](../user-guide/mwe.md)
