# burmesenlp

Myanmar (Burmese) NLP preprocessing toolkit: syllable, word and sentence
segmentation, rule-based POS tagging, and Zawgyi/Unicode conversion.

This is a hardened rewrite of a single-file prototype. Every weak point of
the prototype was addressed:

| Prototype weakness | Fix |
| --- | --- |
| Kinzi (`င်္`) and stack virama emitted as bogus one-char syllables | sylbreak-convention regex handles kinzi and stacked clusters |
| Silent fallback when the dictionary file is missing/corrupt | `LexiconError` is raised; no silent behavior changes |
| Custom dictionary replaced the seed lexicon entirely | Custom `.json`/`.txt` merges onto the seed with tag union |
| No dictionary schema validation | Every entry is validated (word shape, tag names) |
| Conjunctions forced sentence breaks mid-clause | Conjunctions never split; only ။ and strong final particles do |
| `sentence_segment_with_positions` searched normalized text in the raw string | All offsets refer to the normalized text and are guaranteed exact |
| `sentence_word_tags` could desync from `pos_tags` | Words are segmented once and shared by all pipeline stages |
| Multi-char entries in char sets (`ော`, `ေါ`) never matched | Character sets contain single code points only |
| `all(c in digits for c in '')` returned `True` | Empty strings handled explicitly |
| Alphabetical first-tag lookup (`dictionary[word][0]`) | Tags stored in linguistic preference order (function words first) |
| Full trie rebuild on every `add_to_dictionary` | O(1) incremental insert |
| Self-test crashed on Windows cp1252 consoles | CLI reconfigures stdout/stderr to UTF-8 |
| Zawgyi input processed silently | Heuristic detector logs a warning |

## Install

```bash
pip install -e .          # from this directory
pip install -e .[dev]     # with pytest
```

## Quick start

```python
from burmesenlp import BurmeseNLP, process, word_tokenize, pos_tag

# One-shot pipeline
result = process("စာပေကိုဖတ်သည်။သူကစားသည်။")

# Stateful pipeline (custom dictionary, options)
nlp = BurmeseNLP()
nlp.syllable_segment("မြန်မာစာပေ")
nlp.word_segment("မြန်မာစာပေကိုစီစဉ်ခြင်း")
nlp.sentence_segment("စာပေကိုဖတ်သည်။သူကစားသည်။")
nlp.pos_tag(nlp.word_segment("မြန်မာစာပေကိုဖတ်သည်"))

# Engine-dispatched helpers (v1: longest / rule only)
word_tokenize("မြန်မာစာပေ", engine="longest")
pos_tag(["မြန်မာ", "စာပေ"], engine="rule")
```

### Custom dictionary

Custom files **merge** onto the built-in seed lexicon (per-word tag union).
Missing or malformed files raise `LexiconError` — there is no silent fallback.

```python
nlp = BurmeseNLP(dictionary_path="my_dict.json")  # or .txt import
nlp.add_to_dictionary("နည်းပညာ", ["n"])
nlp.save_dictionary("my_dict.json")               # atomic JSON write
```

**Canonical format (JSON)** — what `save_dictionary` writes and round-trips:

```json
{ "word": ["tag1", "tag2"] }
```

**Import format (`.txt`)** — for hand-authored / spreadsheet word lists:

```
word<TAB>tag1,tag2
```

Tags must be from `burmesenlp.POS_TAGS`. To load a file *instead of* the
seed lexicon (no merge), use `BurmeseNLP(lexicon=Lexicon.from_file(path))`.

### CLI

```bash
burmesenlp "မြန်မာစာပေကိုဖတ်သည်။"
burmesenlp --mode words --json "မြန်မာစာပေ"
echo "စာပေကိုဖတ်သည်။" | burmesenlp --mode sentences

# Zawgyi <-> Unicode
burmesenlp --mode zg2uni "ျမန္မာစာေပ"
burmesenlp --mode uni2zg "မြန်မာစာပေ"
burmesenlp --mode to-unicode "ျမန္မာစာေပ"   # detect + convert if needed
```

Output is always UTF-8, including on Windows consoles.

## Conventions and known limitations

- **Syllable convention (sylbreak).** Boundaries follow the widely used
  sylbreak rule (Ye Kyaw Thu et al.): stacked Pali clusters and kinzi stay
  attached to the preceding syllable, e.g. `မန္တလေး → မန္တ | လေး` and
  `အင်္ဂါ → အင်္ဂါ`.
- **Suffix particles are separate words.** Following the ALT / myPOS corpus
  convention, `သည်`, `များ`, `တွေ` etc. are their own tokens rather than
  fused onto the stem.
- **Greedy longest match.** Word segmentation is deterministic greedy
  longest-match against the dictionary, aligned to syllable boundaries and
  never merging across whitespace. It is not globally optimal; accuracy
  scales with dictionary size. The bundled seed lexicon (~150 words) is a
  starting point — load a real lexicon for serious work.
- **Sentence splitting on final particles** is a heuristic (configurable via
  `BurmeseNLP(split_on_final_particles=False)`); quotatives (`ဟု`, `လို့`)
  suppress the split.
- **Zawgyi conversion is available** via `burmesenlp.zg2uni` / `uni2zg` /
  `to_unicode`, or CLI `--mode zg2uni|uni2zg|to-unicode`. Detection is
  heuristic; convert explicitly when you already know the encoding.
- **Positions refer to normalized text** (zero-width characters stripped,
  Unicode NFC). Call `burmesenlp.normalize(text)` to reproduce the exact
  string the offsets index into.

## Development

```bash
pytest
```

## References

- Ding et al. (2016) — Word Segmentation for Myanmar Language
- Ding et al. (2017) — Sentence Segmentation for Myanmar Language
- Ye Kyaw Thu — sylbreak syllable segmentation rule
- ALT Burmese Corpus (2017) — Asian Language Treebank
