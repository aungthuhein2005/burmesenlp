# burmesenlp 1.2.0

This release adds an opt-in fix for a Myanmar text-encoding problem NFC
can't solve, a real evaluation harness with the first published accuracy
numbers for this toolkit, a safer Zawgyi-to-Unicode converter, a
token-cost profiler for LLM users, and a Windows encoding bug fix.
**Nothing in `normalize()`'s or `process()`'s default behavior changes** —
every new capability here is opt-in or lives behind a separate function,
so upgrading is safe for existing code.

## What changed for users

### `canonical_order()` — fixes a real, measured text-matching bug

Two different typing orders can produce the *same-looking* Myanmar
syllable but different underlying text. Unicode's standard normalization
(NFC) does not fix this for Myanmar: NFC's canonical ordering only
reorders marks that carry a nonzero combining class, and nearly every
Myanmar mark — all four medials, every vowel sign — has a combining
class of zero. There is simply no mechanism in NFC that can touch them.
In practice this means two pieces of text that look identical to a
reader, and that a person would expect to match, silently fail to match
in code (search, deduplication, dictionary lookups, etc.).

We measured how often this actually happens on real text: **4.518% of
word tokens in the myPOS corpus** and **5.359% of syllable tokens in
Burmese Wikipedia** — between 1 in 19 and 1 in 22 tokens, depending on
the corpus. Common enough to matter, not a corner case.

`canonical_order()` fixes this by putting Myanmar marks into a single
canonical order. It's **opt-in** — call it yourself when you need it.
`normalize()`'s default output is unchanged, so if your code stores
character offsets computed against burmesenlp 1.1.0 output, those
offsets are still valid after upgrading.

### Zawgyi detection is now calibrated — `to_unicode()` no longer mangles Shan/Mon/Karen text

`to_unicode()` (auto-detect-and-convert Zawgyi text to standard Unicode)
used to rely on a simple heuristic: if it saw certain characters, it
assumed the text was Zawgyi and ran it through a full conversion. The
problem: those same characters are also genuine, legitimate letters in
Shan, Mon, Kayah, Karen, and Rumai Palaung — languages that share those
codepoints with Zawgyi. That heuristic misfired on real Shan text roughly
**100% of the time** and real Mon text roughly **72% of the time**
(measured on real Wikipedia articles), silently corrupting it with no
error message.

`to_unicode()` now uses a calibrated statistical model instead, which
correctly leaves that text alone. If you only use `to_unicode()`, this
is fixed for you automatically.

**If you call `is_zawgyi()` directly, it is unchanged and still has that
problem** — this release intentionally did not change its behavior, to
avoid breaking anyone depending on its exact output. If you need a
reliable answer, use `get_zawgyi_probability()` instead, which is what
`to_unicode()` now uses internally.

This release also ships a new, more transparent conversion path,
`convert_with_report()`, which returns not just the converted text but a
log of exactly which rules fired and where — useful if you need to audit
or debug a conversion rather than just trust it.

### Windows: piping Burmese text into the CLI no longer produces garbage

On Windows, the command-line tool previously read piped input using the
console's default legacy encoding instead of UTF-8. Piping a real
Myanmar text file in produced no error — just silently corrupted output
(mojibake). Typing text directly as a command-line argument was
unaffected; only piped/redirected input was broken. This is fixed: the
CLI now forces UTF-8 on stdin as well as stdout/stderr.

Also added: `burmesenlp --version` at the top level (it previously only
existed on the `bench` subcommand).

### `burmesenlp bench` — the first published, methodology-declared accuracy numbers for this toolkit

Word segmentation accuracy claims are only meaningful if you know exactly
what was measured against what. `burmesenlp bench` is a new evaluation
command that scores segmentation against two independent gold-standard
corpora and reports the numbers plainly:

- **ALT (independent corpus): F1 0.9042** — this is the number to trust
  as a general accuracy estimate, since it has no overlap with this
  package's own data.
- **myPOS, out-of-vocabulary words only: F1 0.7403** — a more honest
  lower bound for words the bundled dictionary hasn't seen before.
- **myPOS, in-dictionary words: F1 0.9516 — flagged as contaminated.**
  The bundled word list is itself derived from myPOS, so scoring against
  myPOS's own vocabulary partly measures the segmenter recovering its
  own dictionary rather than generalizing. We're reporting this number
  for transparency, not presenting it as a real accuracy estimate.

`bench` is also a working tool, not just a source of these three
numbers: `--diff` compares against a pre-computed external segmenter's
output, `--category` buckets disagreements to help prioritize what to
fix next, `--freeze-strata` lets you measure a dictionary/gazetteer
expansion honestly (against a frozen pre-expansion baseline rather than
a moving target), and the ALT corpus is enforced as held-out (requires
`--final`, logs every use) so it stays a trustworthy, un-tuned-against
measurement rather than eroding the same way the myPOS number did.

### Token-fertility profiler (`burmesenlp fertility`, optional extra)

If you're using this text with an LLM API, tokenizer choice matters more
than most people assume. Comparing two OpenAI tokenizer generations on
identical Burmese text, we measured a **3.6x difference in token count
(121 versus 34 tokens on the same test sentence)** between them — a
bigger effect than the language itself. This new profiler measures
actual token cost across several real tokenizers
(OpenAI's `cl100k_base`/`o200k_base`, plus Qwen2.5 and Mistral) so you
can make an informed choice instead of relying on rumored multipliers.
Install with `pip install burmesenlp[fertility]` — it's not part of the
default install.

## Known issues

- **Karen text detection is unresolved.** The calibrated detector
  correctly leaves Shan text alone, and also clears the Mon cases that
  the old heuristic missed for structural rather than character-range
  reasons. Karen is different: isolated Karen letters score 0.89–0.91 on
  the detector and may still be incorrectly converted. We chose not to
  add a workaround for this, because the only cheap fix we found would
  trade a measured problem for an *unmeasured* one on a language we
  don't have test data for — see the CHANGELOG for the reasoning. If you
  work with Karen text, verify `to_unicode()`'s output before trusting it.
- **`is_zawgyi()` (as opposed to `to_unicode()`) is unchanged and still
  has the false-positive rates described above** (~100% on Shan, ~72% on
  Mon text, measured on real Wikipedia articles). It was left as-is
  deliberately, to avoid changing behavior for existing callers. Use
  `get_zawgyi_probability()` if you need a calibrated answer.
- **The full analysis pipeline (`--mode all` / `process()`) is slow on
  large input.** On the same 890KB input: syllable segmentation 0.87s,
  word segmentation 0.99s, POS tagging 1.61s, sentence segmentation
  36.4s. The cost is isolated to the sentence-segmentation stage. Not
  yet fixed; for large volumes use `word_tokenize()` or
  `syllable_tokenize()` directly.
