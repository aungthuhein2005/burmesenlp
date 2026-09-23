# Spell-checking (`burmesenlp.spellcheck`)

Dictionary-based spell-checking over already-**segmented** words (the
output of `word_tokenize()`), not raw sentences — Burmese has no spaces,
so "spell-check this text" only makes sense after segmentation, the same
reason `pos_tag()` also takes a word list rather than a sentence.

```python
from burmesenlp import word_tokenize, is_known, suggest, correct_words

words = word_tokenize("ကျောင်းကိုသွားသည်။")
is_known("ကျောင်")        # False -- a dropped-mark typo of "ကျောင်း" (school)
suggest("ကျောင်")          # ['ကလောင်', 'ကောင်', 'ကျောက်', 'ကျောင်း', 'ကျော်']
correct_words(["ကျောင်"])  # top suggestion applied; word kept unchanged if none found
```

## How it works

Candidate generation is Norvig-style edit distance (delete / transpose /
replace / insert), applied at the Unicode **codepoint** level rather than
the syllable level — a dropped, swapped, or wrong combining mark (asat,
medial, vowel sign) is the realistic Burmese typo shape, and codepoint-level
edits catch that directly. Edit distance 1 is tried first; distance 2 is
only used if nothing at distance 1 is a known word.

Both the query and every lexicon entry are run through
`burmesenlp.canonical_order()` before comparison. The bundled
lexicon's own words are not guaranteed to already be in Table 16-4 canonical
mark order, so canonicalizing only the query would not be enough — a
correctly-spelled word typed in a different (but equally valid) mark order
must resolve to "known," not get flagged as a typo and "corrected" into a
different word.

## Ranking and its known limitation

Suggestions are ranked by edit distance, then **alphabetically** — the
bundled lexicon carries no word-frequency data to break ties more
usefully. This means `suggest()` will sometimes surface a real but rare
word ahead of the common word a human would guess (see the module
docstring example above: `ကျောင်း`, the word actually deleted, is 4th of 5
distance-1 candidates alphabetically). This is a known v1 gap, not an
oversight, and a natural next step if word-frequency data is ever added
to the lexicon.

## Measured false-positive rate

The bundled lexicon is ~24k word-forms; real running text contains
correctly-spelled words outside that set. Measured (not assumed) on 40
random Burmese Wikipedia articles (CC BY-SA, fetched at runtime, never
vendored — same discipline as [`bench`](bench.md)'s corpus handling):

**8.50% of `word_tokenize()` tokens (553 / 6,506) are not in the
spellcheck lexicon** and would be flagged as possible typos.

Spot-checking the unrecognized tokens shows this is not dominated by
genuine core-vocabulary gaps: numerals (`၂၀၁၄`, `၂၀၉၀၉၉`), wiki markup
artifacts (`==`), and Latin-script or transliterated foreign proper nouns
(`Nampayon`, `ဒဂွမ်ဂါး`, `ဂျန်းယန်`) make up a visible share of the sample.
This composition was not independently re-quantified into exact
percentages (a follow-up Wikipedia fetch to do so was rate-limited), so
treat 8.50% as an **upper bound** on the rate of genuinely-common Burmese
words this lexicon doesn't recognize, not a precise "wrong 1 in 12 times"
claim about ordinary vocabulary.

**Practical implication:** treat `suggest()`/`correct_words()` output as
candidates for human review, not an authoritative correction — the same
caution any dictionary-only (non-statistical) spell-checker warrants,
made concrete here with a real number instead of a generic disclaimer.
