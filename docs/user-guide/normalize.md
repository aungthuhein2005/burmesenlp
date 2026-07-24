# Normalization & Zawgyi

## Normalize

```python
from burmesenlp import normalize, looks_like_zawgyi

normalize("စာ\u200bပေ")   # strips zero-width, applies NFC
looks_like_zawgyi("ျမန္မာ")  # heuristic only
```

All pipeline offsets refer to the **normalized** string.

## Zawgyi ↔ Unicode

```python
from burmesenlp import zg2uni, uni2zg, to_unicode, is_zawgyi

zg2uni("ျမန္မာစာေပ")
uni2zg("မြန်မာစာပေ")
to_unicode(text)   # convert if heuristic says Zawgyi
```

!!! warning
    Detection is heuristic. When encoding is known, call `zg2uni` explicitly.
