# Grammar-aware sentences

`SentenceSegmenter.segment_from_chunks` covers the token stream with
non-overlapping phrase chunks (CLAUSE overlays ignored), then:

- Splits on terminal punctuation (`။` `?` `!` …).
- Treats VP / FIXED_VERB / GREETING as predicates.
- Does not split after isolated NP / PP / FIXED_EXPRESSION.
- Optionally soft-splits after a completed predicate when the next unit
  looks like a new sentence onset (`split_on_final_particles=True`).

Character spans for `Document.sentences` are derived from pre-MWE word
token offsets mapped through BMWE merges so
`"".join(sentences) == raw_text`.
