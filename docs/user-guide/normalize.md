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
