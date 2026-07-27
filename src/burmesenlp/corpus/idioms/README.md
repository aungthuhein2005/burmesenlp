# Idioms (BMWE)

Human-editable idiom list used by `BMWEEngine` (autoload on `BurmeseNLP()`).

## Format (V1)

`idioms.json` is a **JSON array of strings** — one surface form per entry:

```json
[
  "အိတ်ပေါက်နှင့် ဖားကောက်",
  "ကံတူ အကျိုးပေး"
]
```

There is **no** required per-entry object metadata such as `{ "text", "type" }`.
Category is inferred from the **resource path** (folder/filename containing
`idiom` → `IDIOM`). Optional overrides: `BMWEEngine.load(..., category=...)`.

Spaces in strings are **not** final token boundaries. The loader uses the same
pipeline word tokenizer (`normalize` → longest match), so spaced and unspaced
variants of the same idiom collapse to one token sequence.

## Cache

`idioms.cache.json` stores pre-tokenized entries. It is used when content
fingerprints of `idioms.json` and the bundled lexicon match; otherwise BMWE
rebuilds the cache (best-effort write).

## Editing

1. Edit `idioms.json` (string list).
2. Run the pipeline or regenerate cache by loading idioms once.
3. Commit both `idioms.json` and an updated `idioms.cache.json` when shipping.
