# Lexicon

Bundled tagged vocabulary plus mergeable custom dictionaries.

```python
from burmesenlp import BurmeseNLP, Lexicon, LexiconError, POS_TAGS

nlp = BurmeseNLP()                          # default lexicon
nlp = BurmeseNLP(dictionary_path="extra.json")  # merge on top
nlp.add_to_dictionary("နည်းပညာ", ["NOUN"])
nlp.save_dictionary("out.json")

# Replace default entirely
nlp = BurmeseNLP(lexicon=Lexicon.from_file("only_mine.json"))
```

## Formats

**JSON:** `{ "word": ["TAG1", "TAG2"] }`

**TXT:** `word<TAB>tag1,tag2`

Tags must be keys of `POS_TAGS`. Missing/malformed files raise `LexiconError`.
