# Normalization & Zawgyi

## Normalize

```python
from burmesenlp import normalize, looks_like_zawgyi

normalize("စာ\u200bပေ")   # strips zero-width, applies NFC
looks_like_zawgyi("ျမန္မာ")  # heuristic only
```

All pipeline offsets refer to the **normalized** string.

!!! important
    `process()` / `BurmeseNLP.process()` call **`normalize()` only**.
    They do **not** auto-convert Zawgyi to Unicode. Convert first when needed.

## Canonical mark order

`normalize()` applies Unicode NFC, but NFC cannot fix Myanmar syllable-mark
order: medials and vowel signs all have `Canonical_Combining_Class` 0, so
two different input-method key orders for the same syllable (e.g. medial ya
before vs. after medial wa) stay distinct strings through NFC forever —
confirmed on the bundled lexicon and a real-corpus scan (myPOS, Burmese
Wikipedia), both showing collision rates over 1% of affected tokens.

```python
from burmesenlp import canonical_order

canonical_order("ကျွန်တော်") == canonical_order("ကွျန်တော်")  # True
```

Opt-in only — not applied inside `normalize()` or `process()`. Call it
explicitly when ingesting text from sources where mark order isn't
guaranteed (user input, mixed-source corpora).

Unicode's own "Contractions" words (e.g. ယောက်ျား "man/husband",
ကျွန်ုပ် "I") spell asat's position as a fixed convention, not an
encoding accident — `canonical_order()` recognizes those exact
documented sequences and passes them through unchanged rather than
sorting them, so an alternate (non-spec) spelling of one of those two
words is not merged with the spec spelling.

## Zawgyi ↔ Unicode

```python
from burmesenlp import zg2uni, uni2zg, to_unicode, is_zawgyi, process

# Opt-in conversion before the pipeline
uni = zg2uni(zawgyi_text)       # when encoding is known
# or:
uni = to_unicode(maybe_zg)      # convert if heuristic says Zawgyi

doc = process(uni)
```

!!! warning
    Detection is heuristic. When encoding is known, call `zg2uni` explicitly.
