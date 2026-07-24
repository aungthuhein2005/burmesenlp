# Pipeline order

```text
Normalize
    → Syllable tokenize
    → Word tokenize (longest)
    → BMWE (token-sequence trie)
    → Contextual POS
    → Phrase chunking
    → Sentence segmentation (chunk/POS-aware)
    → Document
```

Sentence boundaries intentionally come **last**, so subject-marker `သည်`
inside an NP is not confused with sentence-final `သည်` after a VP.
