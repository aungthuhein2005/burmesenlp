# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Keep `__version__` in `src/burmesenlp/__init__.py`, the `version` field in
`pyproject.toml`, and this file in sync on every release.

## [Unreleased]

### Added

- `canonical_order()` in `burmesenlp.normalize`: reorders Myanmar
  syllable-cluster marks (medials, vowel signs, asat) into a canonical
  order. NFC cannot do this (Canonical_Combining_Class 0 on nearly all of
  them), so two different input-method key orders for the same syllable
  stay distinct strings through NFC forever — a real-corpus scan (myPOS +
  Burmese Wikipedia) found this affects 4.5-5.4% of token occurrences.
  Recognizes Unicode's own documented "Contractions" sequences (e.g.
  ယောက်ျား "man/husband") and passes them through unchanged rather than
  sorting them. Opt-in; not applied inside `normalize()` or `process()`.
- `burmesenlp bench`: boundary-level precision/recall/F1 evaluation
  harness for word segmentation against gold corpora (myPOS v3.0 and the
  Myanmar ALT treebank; both CC BY-NC-SA, fetched at runtime, never
  vendored). Supports `--corpus {mypos,alt}`, `--scheme {nopipe,pipe,both}`
  for myPOS (`word_tokenize()` alone vs. `word_tokenize()` + BMWE against
  compound-preserving gold — declared, non-comparable schemes, not two
  cuts of the same number), `--category` (buckets `pipe`-scheme
  disagreements into date/number, productive grammatical derivation,
  proper noun, and genuine-compound candidates — a work queue for growing
  BMWE's trie), and `--diff` against a pre-computed external segmenter's
  output.

  First-ever published F1s for this toolkit, reported as three numbers
  because the myPOS aggregate alone is train-on-test: the bundled
  lexicon's word-form inventory is derived from myPOS (100% of its ~24k
  word-forms appear in myPOS's gold vocabulary — verified, not assumed),
  so `word_tokenize()`'s greedy longest-match partly measures recovering
  its own dictionary's source corpus. myPOS nopipe in-lexicon: F1 0.9516
  (P=0.9900, R=0.9161); myPOS nopipe **OOV** (honest generalization
  estimate): F1 **0.7403** (P=0.6078, R=0.9465); **ALT** (independent
  corpus and word scheme, not implicated in the contamination): F1
  **0.9042** (P=0.8821, R=0.9274, n=20106). See
  `docs/developer-guide/bench.md`.

- `burmesenlp.zawgyi.convert_with_report()`: auditable Zawgyi -> Unicode
  conversion. Unlike `to_unicode()`/`zg2uni()` (both unchanged, still
  silent), this scores each paragraph/segment independently with a
  ported bigram Markov detector (Apache-2.0, from Google's
  myanmar-tools; vendored model file, commit 7d7f7316bd5f, "Retrain
  using new multi-language model"; lazy-loaded, opt-in, adds zero
  overhead to existing calls) instead of the fast codepoint-range
  heuristic in `is_zawgyi()`, and returns a per-rule repair log: which
  of the 118 conversion rules fired, at what original-text offset,
  whether it's a substitution/reorder/length-change, and whether it's
  structurally lossy (multiple distinct Zawgyi inputs collapsing to one
  Unicode output -- 8 of 118 rules do this by construction). Document
  score is reported as `min`/`max`/`spread` across paragraphs, not a
  single average, so a document mixing clean and Zawgyi paragraphs
  doesn't get averaged into a misleading single verdict.

  Motivation, with numbers: `is_zawgyi()`'s codepoint-range check
  (U+1060-1097) is also the Unicode block for Shan/Mon/Kayah/Karen/Rumai
  Palaung letters -- Zawgyi separately reuses those codepoints as glyph
  variants. Measured false-positive rate on real Wikipedia text (25
  articles/language): **Shan**, paragraph-level 100% (207/207
  paragraphs), document-level 100% (25/25) -- the new detector: 0%
  both levels. **Mon**, paragraph-level 62.1% (399/643), document-level
  100% (25/25) -- new detector: 0.2% (1/643), 0% document-level.
  **Karen: not resolved.** No live Karen-language Wikipedia edition
  exists (ksw/kjp checked directly) and a quick eBible lookup did not
  turn up a fetchable corpus either, so no real-text measurement was
  possible. A synthetic probe of individual documented Karen letters
  (Unicode NamesList, U+1061-106D) found the new detector does *not*
  clear the collision the way it does for Shan/Mon: isolated Karen
  consonants score 0.89-0.96 (Zawgyi-like), and 14 of 118 zg2uni rules
  map individual Karen-range codepoints directly to specific Zawgyi
  stacked-consonant shorthand -- a denser, more direct collision than
  Shan's (1 rule, 8 alternatives). Tracked as a known gap (test marked
  `xfail`, not silently passing); real Karen text has not been shown
  safe through this path. See `tests/test_zawgyi_repair.py`.

  Working hypothesis for the Karen gap, **unconfirmed, offered as a
  lead for whoever finds a Karen corpus**: the detector's training
  data plausibly contains Karen-range codepoints only in their
  Zawgyi-shorthand role (consistent with 14 zg2uni rules mapping that
  range 1:1 to specific stacked-consonant forms), so the model learned
  that bigram context as Zawgyi-flavoured rather than as a distinct
  script. Not verified against the training data itself -- inferred
  from the symptom. A hard codepoint-based override was considered and
  rejected: the same 14-rule finding that motivates it also proves the
  Karen range is not unambiguous (Zawgyi genuinely used it), so an
  override would trade a measured false positive for an unmeasured
  false negative on real Zawgyi text, on a language with no corpus to
  check the trade against.

  `ambiguous` on `RepairEntry` (distinct from `lossy`: a context-
  sensitive rule that guesses wrong on some real input, vs. a rule
  that structurally cannot distinguish its inputs) is populated from
  round-trip evidence, not inference. Two directions, run and reported
  separately because they lose different things: (1) zg2uni on real
  Zawgyi text (8 sentence pairs, Rabbit-Converter's own
  `source/res/sample.json` -- WTFPL, the same upstream project the
  rule tables come from) -- 0/8 round-trip failures, too small a
  sample to rule out rare cases but a real, not fabricated, corpus.
  (2) uni2zg then zg2uni on myPOS (500 sentences) -- raw string
  inequality flagged 113/500 (22.6%) as "failures", but nearly all of
  that was a measurement bug caught before publishing: mark-order and
  NFC-precomposition differences that `canonical_order()` + NFC
  already resolve (the same normalization `convert_with_report()`
  applies to its own output). Comparing correctly: **2/500 (0.4%)
  genuine failures**, both traced to the same cause -- rule 67's
  digit-zero/letter-wa heuristic (rules 62-69, 93 collectively guess
  whether a Zawgyi `၀` glyph means the digit zero or the letter wa
  from context, since they render identically) misfiring on a genuine
  decimal zero next to punctuation, e.g. "6.0%" silently becomes
  "6.wa%". Rule 67 is the only rule with `ambiguous=True`; it was not
  one of the 8 statically-flagged `lossy` rules -- found empirically,
  as intended. As a calibration check, the same round trip was run on
  real Shan (n=235) and Mon (n=401) Wikipedia text, canonicalized the
  same way: **100% and 87.5% failure respectively, unchanged by
  canonicalization** -- confirming those are genuine information loss
  (Zawgyi has no representation for these letters), not measurement
  noise. See `research/zawgyi-repair-log/roundtrip_check.py`.

## [1.1.0] - 2026-08-27

### Added

- `engine="xlmr"` POS tagger backed by
  [`aungthuhein-dev/burmese-pos-xlmr`](https://huggingface.co/aungthuhein-dev/burmese-pos-xlmr)
  (XLM-RoBERTa, myPOS tagset). Standalone tagging only, via
  `pos_tag(words, engine="xlmr")`; not wired into `BurmeseNLP.process()`.
  Requires the optional `xlmr` extra (`pip install burmesenlp[xlmr]`).

### Fixed

- Gazetteer entity spans are now locked to `PROPN` in `Document.pos_tags`
  itself, not just inside the phrase chunker. Multi-token names/places no
  longer keep garbage tags on trailing syllables from the context-blind
  first POS pass (e.g. `ထက်` as `CONJ`, `ဘို` as `VERB`).

## [1.0.1] - 2026-08-04

### Fixed

- Terminal vs non-terminal punctuation in sentence segmentation (`၊` no longer
  forces a hard sentence cut like `။`).
- Ambiguous NOUN/VERB stems before AUX (e.g. `ပညာသင်ခဲ့`) now tag as `VERB`.
- Lexicon entry for `ပညာသင်` includes `VERB` so context rules can apply.
- Removed invalid Trove classifier `Natural Language :: Burmese` (PyPI/TestPyPI
  rejected uploads with HTTP 400).
- Removed a zero-width-only junk key from bundled `default.json` (was logging
  on every import); lexicon sanitize skips are now debug-level only.

### Changed

- README / changelog / pipeline docs now describe gazetteer NER, clause
  parsing, and corpus export accurately (NER is list-based, not “absent”).

## [1.0.0] - 2026-07-24

### Added

- Public rule-based Myanmar NLP toolkit: normalize, Zawgyi ↔ Unicode APIs,
  syllable / word segmentation, lexicon, rule-based POS tagging.
- **BMWE** multi-word expression engine (token-sequence trie) with bundled
  `corpus/idioms/idioms.json` and optional `idioms.cache.json`.
- **Phrase chunking** (YAML grammar under `corpus/grammar/`).
- **Gazetteer NER** (list match after POS → `Document.entities`; entity spans
  locked as NP in the chunker).
- **Clause parsing** over phrases → `Document.sentence_trees` / `clauses`.
- **Corpus export** (`CorpusExporter` / `CorpusImporter`: JSONL, CoNLL, BRAT,
  Label Studio).
- **Grammar-aware sentence segmentation** after POS + chunks (no bare
  `သည်`/`တယ်` splits).
- Pipeline order: normalize → syllables → words → BMWE → POS → gazetteer →
  chunk → sentences → clauses → `Document`.
- POS tag `IDIOM` for merged MWEs; MWE-aware tagging.
- Bundled tagged default lexicon (`lexicon/data/*.json`) loaded automatically
  by `BurmeseNLP()` / `process()`.
- High-level `process()` / `BurmeseNLP` and `burmesenlp` CLI.
- MkDocs Material documentation (`docs/`, `mkdocs.yml`) and GitHub Pages
  workflow (`.github/workflows/docs.yml`).
- Golden regression tests, packaging smoke checks, and CI (pytest, ruff, mypy).
- Apache-2.0 license, contributing guide, code of conduct, and security policy.

### Notes

- Version 1 is **rule-based only**. It does not include machine learning,
  Transformers, CRF, SentencePiece, embeddings, sentiment, or spell checking.
  NER in V1 is **gazetteer / list-based** (not statistical or neural).
- `process()` does **not** auto-convert Zawgyi; use `zg2uni` / `to_unicode`
  when the encoding is known or suspected.
