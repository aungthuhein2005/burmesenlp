# Longest-match word segmentation

Greedy longest dictionary match aligned to syllable boundaries.

- Matches cannot split a syllable.
- No merge across whitespace (token adjacency required).
- Grammatical suffixes (`သည်`, `များ`, …) stay separate tokens (myPOS-style).
- Digit + classifier may fuse (e.g. `သုံးခု`).

Deterministic and fast; not globally optimal. Larger lexicons or statistical
engines can plug in later via `tokenize.engine`.
