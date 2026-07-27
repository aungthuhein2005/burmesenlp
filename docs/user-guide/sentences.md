# Sentence segmentation

Sentences are split **after** POS and phrase chunking — not by matching
`သည်` / `တယ်` alone. `ClauseParser` then builds nested
`Sentence → Clause → Phrase` trees inside each sentence
(`doc.sentence_trees`).

```python
from burmesenlp import BurmeseNLP, sentence_tokenize

nlp = BurmeseNLP()
nlp.sentence_segment(
    "မင်္ဂလာပါ။ ကျွန်တော်တို့သည် မြန်မာဘာသာစကားကို လေ့လာနေကြသည်။"
)
# ['မင်္ဂလာပါ။', 'ကျွန်တော်တို့သည် မြန်မာဘာသာစကားကို လေ့လာနေကြသည်။']

sentence_tokenize("သူသည် ကျောင်းကို သွားသည်။")
# one sentence — first သည် is POSTP, not a boundary
```

## Rules (summary)

1. Never split only because a token equals `သည်` / `တယ်` / `ပါ`.
2. Prefer a completed predicate (VP / GREETING) before ending a sentence.
3. Split on `။` `?` `!` `…`, end of text, or (optionally) completed VP
   followed by a new NP onset.
4. Isolated NP / PP does not end a sentence.

`BurmeseNLP(split_on_final_particles=False)` disables soft VP→NP splits
(punctuation-only mode).
