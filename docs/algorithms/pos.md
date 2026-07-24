# Rule POS

Stages:

1. **Candidates** — lexicon + closed-class heuristics (incl. `သည်` as
   `POSTP`/`SFP`/`PART`).
2. **Context rules** — filter per token (subject marker vs finite particle).
3. **Grammar / sequence rules** — multi-token patterns.
4. **Preference** — `TAG_PREFERENCE` among remaining tags.

BMWE indices override candidates to the span's resolved POS before
disambiguation.
