# Pipeline order

Verified against `BurmeseNLP._analyze()`:

```text
Normalize
    → Syllable tokenize
    → Word tokenize (longest)
    → BMWE (token-sequence trie)
    → Contextual POS (MWE-aware)
    → Gazetteer NER (list match → Document.entities)
    → Phrase chunking (entity spans locked as NP)
    → Sentence segmentation (chunk/POS-aware)
    → Clause parse (→ Document.sentence_trees / clauses)
    → Document
```

Gazetteer matching runs **after** POS on post-BMWE words — POS tags are one
of the signals `GazetteerManager.find_all` uses to reject short/ambiguous
false-positive matches. Once a span is confirmed, every token in it is
locked to `PROPN` **in `pos_tags` itself** (not just inside the chunker), so
a name's trailing syllables don't keep whatever tag the context-blind first
POS pass gave them (e.g. `ထက်` as `CONJ`, `ဘို` as `VERB`) once we know
they're part of one name. The chunker then locks the same span to one NP so
names are not split by POS patterns.

Sentence boundaries intentionally come **after** POS + chunks, so
subject-marker `သည်` inside an NP is not confused with sentence-final `သည်`
after a VP. Clause parsing runs last over the phrase covering within each
sentence window.
