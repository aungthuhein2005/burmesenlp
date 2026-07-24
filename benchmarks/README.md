# Benchmarks

Lightweight, **manual** checks for BurmeseNLP V1. Not a CI gate.

## What is measured

| Script | Metric | Notes |
| --- | --- | --- |
| `speed_smoke.py` | sentences/sec for `process()` | Fixed sample list; wall-clock |

## What is **not** measured (deferred)

- Tokenization / POS Precision, Recall, F1 (needs gold labels)
- Per-tag accuracy tables
- Memory profiling beyond a rough optional note

## Run (from repo root)

```bash
pip install -e .
python benchmarks/speed_smoke.py
python benchmarks/speed_smoke.py --repeat 50
```

Example output:

```text
sentences=8 repeat=20 elapsed_s=... sentences_per_sec=...
```

Results vary by machine and cold-start lexicon/BMWE load (first call is slower).
