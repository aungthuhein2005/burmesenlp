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

Gazetteer matching runs **after** POS on post-BMWE words. Matching spans are
also forced to one NP in the chunker so names are not split by POS patterns.

Sentence boundaries intentionally come **after** POS + chunks, so
subject-marker `သည်` inside an NP is not confused with sentence-final `သည်`
after a VP. Clause parsing runs last over the phrase covering within each
sentence window.
