# Pipeline & Document

`process(text)` and `BurmeseNLP.process(text)` run the full V1 stack once and
return a [`Document`](../api/pipeline.md).

Input is expected to be **Unicode Myanmar** text. The pipeline runs NFC /
zero-width cleanup via `normalize()`; it does **not** call `zg2uni`. Convert
Zawgyi with `zg2uni` / `to_unicode` before `process()` when needed
(see [Normalization & Zawgyi](normalize.md)).

## Order

Verified against `BurmeseNLP._analyze()`:

1. Normalize
2. Syllable tokenize
3. Word tokenize (longest match)
4. BMWE merge
5. POS tag (MWE-aware)
6. Gazetteer NER → `doc.entities` (skip with `gazetteer=False`)
7. Phrase chunk (entity spans locked as NP)
8. Grammar-aware sentence segment
9. Clause parse → `doc.sentence_trees` / `doc.clauses`

## Document fields

| Field | Meaning |
| --- | --- |
| `raw_text` | Normalized input |
| `syllables` | Syllable strings |
| `words` | Post-MWE word tokens |
| `sentences` | Sentence strings (partition of `raw_text`) |
| `pos_tags` | `(word, tag)` pairs aligned with `words` |
| `sentence_word_tags` | Per-sentence slices of `pos_tags` |
| `mwe` | Merged `MWEToken` spans |
| `entities` | Gazetteer NER hits (`PERSON` / `TOWN` / …) |
| `chunks` | Phrase `Chunk` objects |
| `sentence_trees` | Per-sentence syntax with nested phrases + clauses |
| `clauses` | Flat list of clauses from `sentence_trees` |

## Serialization

```python
doc = process("စာဖတ်သည်။")
payload = doc.to_dict()          # plain dict
doc.to_json(ensure_ascii=False)  # JSON string
```

Mapping-style access still works: `doc["words"]`, `"chunks" in doc`,
`"entities" in doc`, `"clauses" in doc`.

For training-oriented formats (JSONL / CoNLL / BRAT / Label Studio), use
[`CorpusExporter`](../api/export.md).

## Consistency

```python
assert "".join(doc.sentences) == doc.raw_text
assert len(doc.pos_tags) == len(doc.words)
flat = [p for sent in doc.sentence_word_tags for p in sent]
assert flat == doc.pos_tags
```
