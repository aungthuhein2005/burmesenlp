# Phrase chunking

YAML-driven shallow chunker over words + POS.

```python
from burmesenlp import chunk, BurmeseNLP

chunk("ကျွန်တော်ကျောင်းသို့သွားသည်။")

nlp = BurmeseNLP()
doc = nlp.process(text)
for c in doc.chunks:
    print(c.type, c.text, c.start, c.end)
```

## Chunk types

| Type | Meaning |
| --- | --- |
| `NP` | Noun phrase |
| `VP` | Verb phrase |
| `PP` | Postpositional phrase |
| `ADJP` / `NUMP` | Adjective / numeral phrases |
| `CLAUSE` | Clause span from markers |
| `GREETING` / `FIXED_EXPRESSION` / `FIXED_VERB` | Exceptions & idioms |

Grammar files live under `src/burmesenlp/corpus/grammar/`:

- `phrase_rules.yml`
- `phrase_markers.yml`
- `phrase_exceptions.yml`

`IDIOM` POS tokens chunk as `FIXED_EXPRESSION`.
