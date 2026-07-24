# BMWE trie

Burmese Multi-Word Expression engine matches **token sequences**, not raw
substrings.

1. Load corpus strings → normalize → **same** word tokenizer as the pipeline.  
2. Insert multi-token entries into a trie.  
3. At runtime, greedy left-to-right: at each index, collect trie hits, pick
   best by priority then length, optionally validate, emit one merged token.

Category defaults to POS: `IDIOM` → tag `IDIOM`; org/location/person → `NOUN`.

Cache file `idioms.cache.json` stores pre-tokenized entries keyed by content
fingerprints of the idiom list and lexicon data.
