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

## Alternate engine: `engine="xlmr"`

An XLM-RoBERTa model fine-tuned on the
[myPOS tagset](https://huggingface.co/aungthuhein-dev/burmese-pos-xlmr) is
available as a second engine, for standalone tagging only:

```python
from burmesenlp import pos_tag

pos_tag(words, engine="xlmr")  # myPOS labels: n, v, ppm, part, conj, ...
```

Requires the `xlmr` extra (`pip install burmesenlp[xlmr]`; pulls in
`transformers`/`torch`, imported lazily). Its label set does **not** match
the rule engine's tagset above (no `PROPN`, no `SFP`/`PART`/`AUX` split), so
it is not wired into `BurmeseNLP.process()` — chunking, sentence
segmentation, and clause parsing all assume `engine="rule"` tags.
