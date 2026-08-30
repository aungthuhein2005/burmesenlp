# CLI internals: encoding, file handling, and known limits

## stdin encoding — fixed in 1.2.0, tested so it stays fixed

Windows defaults `sys.stdin`/`sys.stdout`/`sys.stderr` to the console's
legacy code page (`cp1252` observed), not UTF-8. `cp1252` can't represent
Myanmar script, but it also doesn't raise on arbitrary UTF-8 bytes — it
silently mis-decodes them (mojibake) instead of failing. A user piping a
real Myanmar text file into the CLI on Windows got corrupted input with
no error, while the module docstring claimed UTF-8 safety on every
platform. Only found by actually piping real Myanmar text through and
looking at the output, not by reading the code.

Fixed by reconfiguring all three streams to UTF-8 (`_force_utf8_streams()`
in `cli/__init__.py`), not just stdout/stderr as before. Regression-tested
in `tests/test_cli_stdin_utf8.py` via a real subprocess with a real piped
stdin and every UTF-8-forcing environment override stripped — an
in-process stand-in can't reproduce a *default* codec choice, so the test
has to actually exercise it.

## `segment_file()` — not added; the existing path already covers it

The PRD proposed a `segment_file()` convenience wrapper for large-file
input. Measured before building it, per this project's usual discipline:
the existing CLI (`burmesenlp --mode words < file.txt` /
`word_segment()`/`syllable_segment()` called directly) reads the whole
input into memory rather than streaming — but at realistic corpus scale
that doesn't matter in practice. The full 9.5MB myPOS v3.0 corpus through
`--mode syllables` completes in ~11 seconds, unstreamed. A wrapper that
just opens a file and calls the same segmentation functions would add a
convenience shim, not new capability or better performance. Decision:
dropped from the PRD, not silently omitted — this is the record of why.

If a genuinely huge input (hundreds of MB+) turns out to matter later,
the right fix is a real streaming/chunked segmenter, not a thin
`segment_file()` wrapper around the current in-memory path — a wrapper
would still slurp, just with an extra layer of API.

## `--mode all` (the full pipeline) does not scale to large files — known limitation, not yet fixed

Segmentation-only modes scale close to linearly and are fine at
multi-megabyte input. The full pipeline (`process()`, i.e. `--mode all`)
does not, and the gap is large enough to matter well before "large file"
territory. Measured on the same 890KB slice of myPOS v3.0 (no
pipeline-specific tuning, plain wall-clock):

| mode | what it runs | time |
|---|---|---|
| `syllables` | normalize + syllable segment | 0.87s |
| `words` | + word segment (BMWE) | 0.99s |
| `pos` | + POS tagging | 1.61s |
| `sentences` | + grammar-aware sentence segmentation (`_analyze()`) | **36.4s** |
| `all` (`process()`) | + gazetteer NER + phrase chunking + ClauseParser | 36.0s |

Two things worth noting for whoever picks this up:

1. **The jump is entirely between `pos` and `sentences`** — a ~22x
   increase for the same input, isolated by timing each existing CLI
   mode rather than guessing. Whatever `sentence_segment()`/`_analyze()`
   does beyond word-segment-then-POS-tag is the thing to profile first.
2. **`process()` adds nothing further on top of that** — `all` (36.0s)
   and `sentences` (36.4s) are within noise of each other, meaning
   gazetteer NER, phrase chunking, and ClauseParser are cheap relative to
   whatever `_analyze()` is already paying for sentence boundaries. Don't
   spend investigation time there; it isn't where the cost is.

The PRD never specified full-pipeline throughput on large input, so this
is a discovered constraint, not a missed requirement. Not investigated
further or optimized here — flagging with enough detail that the next
pass doesn't have to re-derive it from scratch.
