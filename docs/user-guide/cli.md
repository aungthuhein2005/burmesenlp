# CLI

```bash
burmesenlp --mode words "ကျွန်တော်ကျောင်းသို့သွားသည်။"
burmesenlp --json --mode process "စာပေကိုဖတ်သည်။"
burmesenlp --mode zg2uni "ျမန္မာစာေပ"
```

Common modes: `process`, `words`, `sentences`, `syllables`, `pos`, `zg2uni`, `uni2zg`.

## `burmesenlp bench`

Boundary-level P/R/F1 for word segmentation against gold corpora, fetched
at runtime (never vendored). See
[Evaluation (bench)](../developer-guide/bench.md) for the full picture —
in particular, why a `nopipe` score and a `pipe` score are not the same
gold standard and must never be compared to each other.

```bash
burmesenlp bench --scheme nopipe
```
