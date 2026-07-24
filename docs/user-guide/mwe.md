# Multi-word expressions (BMWE)

After word tokenization, `BMWEEngine` merges known multi-word expressions
(idioms, and optionally organizations / locations / persons).

## Automatic (pipeline)

```python
from burmesenlp import BurmeseNLP

nlp = BurmeseNLP()  # autoloads corpus/idioms/idioms.json
doc = nlp.process("ဒီကောင် အိတ်ပေါက်နှင့် ဖားကောက် နေတာပါကွာ။")
doc.words   # idiom joined into one token
doc.mwe     # MWEToken(category="IDIOM", pos="IDIOM", ...)
```

Merged idioms receive POS tag **`IDIOM`** (not unknown → `VERB`).

## Standalone

```python
from burmesenlp import BMWEEngine, word_tokenize

engine = BMWEEngine()
words = word_tokenize("ကံတူအကျိုးပေး")
engine.process(words)
merged, spans = engine.process_detailed(words)
```

## Loading extra lists

```python
nlp.load_mwe("path/to/organization/orgs.txt")  # category from path
nlp.load_mwe("extra.json", category="IDIOM", priority=10)
```

Formats: JSON string array, or TXT one expression per line (`#` comments OK).

## Tokenization contract

The loader uses the **same** word tokenizer as the pipeline (`normalize` →
longest match). Spaces in corpus strings are ignored for matching, so spaced
and unspaced idiom spellings collapse to one token sequence.

Tokenized entries are cached in `idioms.cache.json` when fingerprints match.
