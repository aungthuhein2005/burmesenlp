# Evaluation (`burmesenlp bench`)

Boundary-level precision/recall/F1 for word segmentation, against gold
corpora fetched at runtime — never vendored, since every corpus wired in
is CC BY-NC-SA or stricter.

```bash
burmesenlp bench --scheme nopipe   # word_tokenize() alone (default)
burmesenlp bench --scheme pipe     # word_tokenize() + BMWE, compound-preserving gold
burmesenlp bench --scheme both     # run both, report separately
burmesenlp bench --corpus alt      # independent corpus, independent of the lexicon
```

## Read this before quoting a number from here

**The myPOS `nopipe` aggregate (F1 0.9507) is train-on-test and must never
be quoted alone.** The bundled lexicon's word-form inventory is derived
from myPOS — verified empirically, not assumed: 100% of the lexicon's
~24k word-forms appear in myPOS v3.0's gold vocabulary, which does not
happen between independently-compiled resources by chance. `word_tokenize()`
is greedy longest-match over that lexicon, so scoring it against myPOS
measures how well it recovers the corpus its own dictionary came from,
not general segmentation ability.

Three numbers, not one:

| | P | R | F1 | n |
|---|---|---|---|---|
| myPOS nopipe, in-lexicon boundaries | 0.9900 | 0.9161 | 0.9516 | 43196 sentences (97.72% of gold vocabulary is in-lexicon) |
| myPOS nopipe, **OOV boundaries** (honest generalization estimate) | 0.6078 | 0.9465 | **0.7403** | same corpus, 2.28% of vocabulary |
| **ALT** (independent corpus, independent word scheme, not implicated in the lexicon contamination) | 0.8821 | 0.9274 | **0.9042** | 20106 sentences |

The ~21-point F1 gap between in-lexicon and OOV strata on myPOS is how
much of the aggregate 0.9507 is memorized vocabulary rather than method.
`--scheme nopipe` always prints this stratified breakdown, with the
caution, alongside the aggregate — never emit the aggregate alone.

## Why boundary-level, not token accuracy

Each segmentation is a set of boundary character offsets; scoring is set
overlap. One wrong boundary costs exactly one boundary — token accuracy
would double-count it (a wrong split corrupts two adjacent tokens).

## Two schemes are not the same gold standard

myPOS v3.0 ships two word-boundary conventions in the *same* corpus:

- `nopipe` — compound words flattened; matches `word_tokenize()`'s own
  granularity (compound/idiom merging is the separate, later BMWE
  stage).
- `pipe` — myPOS's own `\|` compound marker preserved and merged into
  one gold token, for scoring `word_tokenize()` + BMWE together.

Never compare a `nopipe` score to a `pipe` score, or to any published
number that doesn't state its scheme — myPOS and ALT disagree with each
other about what a Burmese word is, and published Burmese segmentation
figures (90-94%, ~80%) are unusable as targets for exactly this reason.
The output header always states corpus, scheme, n, and which pipeline
stages were active.

## Before trusting a `pipe`-scheme F1

BMWE's compound trie and myPOS's `\|` convention were built independently.
`--scheme pipe` always prints a sample of BMWE-vs-gold disagreement
positions (spread across distinct sentences, not just the first N) before
the score — read it. A large gap between `nopipe` and `pipe` F1 is not
automatically "BMWE is broken"; it can just as easily mean the gold
scheme is measuring something broader than compound/idiom merging (e.g.
myPOS marks productive grammatical derivations and proper-noun phrases
with `\|` too, which are arguably other pipeline stages' jobs, not
BMWE's).

## `--category`

`--scheme pipe --category` buckets the disagreement audit into
`date_number` / `productive_derivation` / `proper_noun` / `genuine_compound`
(the actual work queue for growing BMWE's trie) instead of a flat sample.
On the full corpus: 1609 date/number, 5084 productive grammatical
derivation (`-မှု`/`-ရေး` nominalizers — a regular grammar pattern, not
idiom material), 2397 proper nouns the gazetteer already catches, and
17583 in the `genuine_compound` fallback bucket. That fallback bucket is
a ceiling, not a confirmed count — it still contains definitional cases
the three heuristics don't catch (e.g. a span crossing a grammatical
particle like ကို/၏/သို့/နှင့်), so treat it as a work queue to skim, not
a ready-made bug list.

The `proper_noun` heuristic checks the toolkit's *own* gazetteer — so a
known gazetteer gap falls through to `genuine_compound` too. Two
confirmed examples sitting there right now: `ရန်ကုန်မြို့` ("Yangon City")
and `ဗိုလ်ချုပ်အောင်ဆန်း` ("General Aung San") are not gazetteer hits.
That's unclaimed work between BMWE and the gazetteer, not a bug in this
categorizer — noted here, not fixed.

## `--freeze-strata` — measuring a lexicon/gazetteer expansion honestly

OOV is defined relative to the lexicon. Expanding the lexicon moves
tokens from OOV to in-vocabulary, so a naive before/after comparison of
the OOV stratum scores a *different token set* each time — that measures
set composition, not accuracy.

```bash
burmesenlp bench --scheme nopipe --freeze-strata baseline.json   # run BEFORE any expansion — creates the snapshot
# ... expand the lexicon ...
burmesenlp bench --scheme nopipe --freeze-strata baseline.json   # run AFTER — reuses the same snapshot
```

The first run for a given path creates it from the *current* lexicon —
run this before changing a single entry. Every later run with the same
path reuses that frozen vocabulary to decide stratum membership, while
`word_tokenize()` itself still uses the live (possibly-expanded) lexicon
to produce hypotheses — so a name that moves from OOV to correctly
segmented after expansion shows up as an OOV-stratum improvement, not as
a token quietly relabeled into the IV stratum. Works for both `--corpus
mypos` and `--corpus alt`. Always report the overall (unstratified) F1
alongside — it's stable under vocabulary changes and can't be gamed this
way.

## ALT is held out — `--final` is required to score it

Decision, enforced in the tool, not just documented: iterate against
`--corpus mypos` during development (already known-contaminated, so
iterating on it costs nothing additional); score `--corpus alt` only for
a measurement you intend to report. Repeatedly checking ALT during a
tuning loop ("add names → score ALT → repeat") is the myPOS contamination
story again, arriving more slowly.

`--corpus alt` refuses to run without `--final`. Every `--final` run is
appended to a persistent log (`alt_holdout_log.jsonl` in the corpus cache
dir) with a timestamp and `--reason`; a second `--final` run prints a
warning listing every prior run, so repeat use is visible in any report
rather than silently possible. Not a hard block past the first use —
enforcement is the deliberate flag plus the audit trail, not a counter.

## Gazetteer changes are invisible to `bench` — know this before measuring one

`word_tokenize()` (what `--scheme nopipe` scores) is pure lexicon
longest-match; `+BMWE` (`--scheme pipe`) adds idiom merging. Neither
consults the gazetteer — `GazetteerManager` runs strictly *after* both,
in `BurmeseNLP._analyze()`, only labeling spans of already-final tokens.
It never merges tokens or feeds back into segmentation. Adding entries to
`corpus/gazetteers/*.json` alone therefore cannot move any `bench` score,
regardless of the data's quality — checked directly against
`WordSegmenter`, `BMWEEngine`, and `tokenize/`: zero references to
`gazetteer` anywhere in that path.

For a gazetteer expansion to be `bench`-measurable, confirmed entries
need to also go into the **lexicon** (as `NOUN` — the lexicon's
`POS_TAGS` has no `PROPN`; that tagging is applied downstream, once the
gazetteer also recognizes the span, via the entity-lock mechanism in
`pipeline/__init__.py`). Gazetteer-only additions are real work (entity
typing, attributes) but will read as a flat `0.0000` change here — that's
wiring, not evidence about whether named entities matter.

## `--diff`

Compares against a pre-computed external segmenter's output (one
sentence per line, space-separated words, line-aligned to the gold
corpus) — e.g. myWord or mmCRFseg output you generated yourself:

```bash
burmesenlp bench --diff myword=myword_output.txt
```

`bench` cannot run third-party segmenters itself.

## Licensing

Every gold corpus here is CC BY-NC-SA (NonCommercial) — cached locally on
first use, never shipped in the burmesenlp wheel. This also means: do not
persist data *derived* from these corpora (n-gram counts, frequency
tables) into Apache-2.0 code — see the `burmesenlp.bench` module
docstring.
