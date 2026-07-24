# Tutorial: process a document

```python
from burmesenlp import BurmeseNLP
import json

nlp = BurmeseNLP()
text = "မင်္ဂလာပါ။ ကျွန်တော်တို့သည် မြန်မာဘာသာစကားကို လေ့လာနေကြသည်။"
doc = nlp.process(text)

print("sentences:", [s.strip() for s in doc.sentences])
print("words:", doc.words)
print("pos:", doc.pos_tags)
print("chunks:", [(c.type.value, c.text) for c in doc.chunks])
print("mwe:", [(m.category, m.text) for m in doc.mwe])

with open("out.json", "w", encoding="utf-8") as f:
    json.dump(doc.to_dict(), f, ensure_ascii=False, indent=2)
```

Expected: two sentences; subject-marker `သည်` tagged `POSTP`; final `သည်`
tagged `SFP`.
