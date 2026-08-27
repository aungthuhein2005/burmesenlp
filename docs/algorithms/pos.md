# Rule POS

`engine="rule"` (the default, and the only engine wired into
`BurmeseNLP.process()`). Stages:

1. **Candidates** — lexicon + closed-class heuristics (incl. `သည်` as
   `POSTP`/`SFP`/`PART`).
2. **Context rules** — filter per token (subject marker vs finite particle).
3. **Grammar / sequence rules** — multi-token patterns.
4. **Preference** — `TAG_PREFERENCE` among remaining tags.

BMWE indices override candidates to the span's resolved POS before
disambiguation. Confirmed gazetteer entity spans similarly override the
final tags to `PROPN` afterward — see [Pipeline order](pipeline.md).

`engine="xlmr"` is a second, unrelated engine (see
[POS tagging](../user-guide/pos.md#alternate-engine-enginexlmr)): a
transformer model with its own myPOS-style tagset, standalone only.
