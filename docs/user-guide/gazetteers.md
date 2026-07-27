# Gazetteers (NER)

Rule-based entity lists under `corpus/gazetteers/`. In V1 they run **inside**
`process()` after POS, on post-BMWE `words`, and fill `doc.entities`.

```python
from burmesenlp import BurmeseNLP, EntityType

nlp = BurmeseNLP()  # gazetteer=True by default (lazy-loaded)
doc = nlp.process("ဒေါ်အောင်ဆန်းစုကြည် ရန်ကုန်ကို သွားသည်။")

for e in doc.entities:
    print(e.text, e.entity_type, e.attributes)

# Skip NER when you only need syntax
nlp = BurmeseNLP(gazetteer=False)
```

## Pipeline placement

```
… → BMWE → POS → Gazetteer → Phrase chunking (entity spans → NP) → …
                      │                    │
                      ▼                    ▼
                doc.entities         doc.chunks (NP with features.entity)
```

Entities remain a **separate** semantic list. Matching spans are also
locked as one `NP` in `chunks` so names are not split by POS patterns
(e.g. `မင်း` PRON + `လှိုင်အစိုးရရဲ့` PP).

## Attributes

Name lists store gender metadata:

```python
{"gender": "male", "source": "male_names"}
{"gender": "female", "source": "female_names"}
```

## Standalone use

```python
from burmesenlp import GazetteerManager

gaz = GazetteerManager()
gaz.contains("ရန်ကုန်")
gaz.lookup("ရန်ကုန်")
```

Most files are JSON string arrays; type comes from the filename
(`towns.json` → `TOWN`, `male_names.json` → `PERSON`, …).
