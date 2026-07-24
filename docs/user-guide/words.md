# Syllables & words

## Syllables

```python
from burmesenlp import syllable_tokenize, BurmeseNLP

syllable_tokenize("မြန်မာစာပေ")
BurmeseNLP().syllable_segment("မြန်မာစာပေ")
```

Whitespace is skipped (not emitted as tokens).

## Words

Dictionary **longest-match** over syllables (`engine="longest"`):

```python
from burmesenlp import word_tokenize

word_tokenize("ကျွန်တော်ကျောင်းသို့သွားသည်", engine="longest")
```

Words never merge **across** whitespace. Contiguous Myanmar runs are segmented
with the lexicon.

Quality depends on lexicon coverage; longer dictionary entries win locally.
