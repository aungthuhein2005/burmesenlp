# Tutorial: custom lexicon

```python
from burmesenlp import BurmeseNLP, Lexicon

# Merge extras onto the bundled default
nlp = BurmeseNLP(dictionary_path="my_terms.json")
nlp.add_to_dictionary("ဒေတာသိပ္ပံ", ["NOUN"])
print(nlp.word_segment("ဒေတာသိပ္ပံကိုလေ့လာသည်"))

# Or start from a file alone
lex = Lexicon.from_file("my_terms.json", merge_default=False)
nlp = BurmeseNLP(lexicon=lex)
```

JSON shape:

```json
{
  "ဒေတာသိပ္ပံ": ["NOUN"]
}
```
