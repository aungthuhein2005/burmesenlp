# POS tagging

Rule-based tagger (`engine="rule"`): lexicon candidates → context filters →
grammar filters → preference fallback.

```python
from burmesenlp import pos_tag, POS_TAGS, BurmeseNLP

pos_tag(["ကျွန်တော်", "ကျောင်း", "သို့", "သွား", "သည်"], engine="rule")
list(POS_TAGS)  # NOUN, VERB, POSTP, SFP, IDIOM, ...
```

## Ambiguous particles

`သည်` / `တယ်` can be:

| Context | Tag |
| --- | --- |
| Subject / topic marker (`သူသည် ကျောင်း…`) | `POSTP` |
| Verb-phrase final (`…သွားသည်။`) | `SFP` |

BMWE spans force their resolved POS (e.g. `IDIOM`) before disambiguation.

## Pipeline

```python
nlp = BurmeseNLP()
doc = nlp.process(text)
doc.pos_tags
```
