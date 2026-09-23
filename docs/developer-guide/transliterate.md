# Romanization (`burmesenlp.transliterate`)

Burmese-to-Latin romanization using **BGN/PCGN**, the 1970 US Board on
Geographic Names / UK Permanent Committee on Geographical Names agreed
system -- a place-name-oriented, **tone-dropping** system, not MLC's own
MLCTS standard (which marks tone and is orthography- rather than
pronunciation-based). Only BGN/PCGN is implemented; do not assume this
output is authoritative for formal Myanmar-language publishing.

```python
from burmesenlp import romanize

romanize("ရန်ကုန်")            # "yangôn"  (Yangon)
romanize("ပြင်ဦးလွင်")         # "pyinulwin"  (Pyin Oo Lwin)
romanize("မင်္ဂလာ")            # "mingala"
```

## Source

Read directly from the primary document, not a paraphrase: the joint
US/UK PDF "ROMANIZATION OF BURMESE, BGN/PCGN 1970 Agreement" (checked
for validity and accuracy, October 2017):
<https://assets.publishing.service.gov.uk/media/5ab4dec7ed915d78bc23450f/ROMANIZATION_OF_BURMESE.pdf>
(byte-identical US mirror at
<https://geonames.nga.mil/geonames/GNSSearch/GNSDocs/romanization/ROMANIZATION_OF_BURMESE.pdf>).

Verified against the source document's own worked examples (its Notes
2-5): မဒမ→madama, အက→aga, ကလိ→kali, သာငယ်→thangè, အိုဘဲ့→obè, အပ်→at,
သဒ္ဓ→thadda — and, independently, against the well-known place names
ရန်ကုန်→Yangon and ပြင်ဦးလွင်→Pyin Oo Lwin. All of these are regression
tests in `tests/test_transliterate.py`.

## Measured coverage

Running `romanize()` over all ~24k bundled-lexicon words and checking
for leftover unromanized Myanmar characters in the output: **99.83%
(23,846 / 23,886) romanize completely.** The remaining 0.17% are, by
inspection: Myanmar punctuation/grammatical symbols outside BGN/PCGN's
scope (၊ ။ ၌ ၍), the two documented `normalize()` Contraction words (see
below), and a handful of genuinely rare or ambiguous orthographic edge
cases (e.g. kinzi immediately following a syllable that already has its
own vowel sign). Any syllable this module cannot confidently romanize
is left as the original Myanmar text in the output, never guessed.

## Kinzi: not in the source, verified another way

The source document does not mention kinzi (the prefixed nga+asat+virama
unit, e.g. the "ç်္" in မင်္ဂလာ) at all. Its romanization here is this
module's **own inference**, cross-validated against well-known
conventional spellings rather than guessed: treating kinzi as merging
into the preceding syllable exactly like a plain-context "in" final (the
same value row 2 of the source's final-consonant table gives for a
plain **ç** final) correctly reproduces မင်္ဂလာ→**ming**ala and
စင်္ကာပူ→**sin**gabu. This only applies when the preceding syllable has
no vowel sign of its own; kinzi following a vowel-bearing syllable is an
unverified combination and is passed through unromanized.

## Deliberately out of scope for this v1

See the full list with reasoning in
[`bgn_pcgn.py`](https://github.com/aungthuhein2005/burmesenlp/blob/main/src/burmesenlp/transliterate/bgn_pcgn.py)'s
module docstring. In short: the source's own Note 6 hyphen
disambiguation (`kun-yet` vs `kunyet`), Note 8's rare vowel-shifting
spelling idiom, the two documented Contraction words, and Note 4's
word-*internal* vowel-initial-syllable hyphen (needs syllable-boundary
information this module doesn't have) are all left unimplemented rather
than guessed at.

## Refactor note

`romanize()` and `canonical_order()` (in `burmesenlp.normalize`) share
one internal cluster parser, `_iter_clusters()` -- extracted from
`canonical_order()`'s own cluster-splitting loop with a full test-suite
pass confirming zero behavior change before anything romanization-shaped
was built on top of it. This is why both features agree on what counts
as one syllable cluster (kinzi, a stacked/subjoined consonant, and the
run of reorderable marks that follows).
