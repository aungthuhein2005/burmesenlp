# Roadmap

| Version | Focus |
| --- | --- |
| **1.x** | Rule-based toolkit (normalize, tokenize, BMWE, POS, chunk, sentences) |
| **2.x** | Hybrid NLP — statistical engines via registries; optional `burmesenlp-models` |
| **3.x** | Deep learning backends |
| **4.x** | Research platform (e.g. EvoPiece, benchmarks) |

## Documentation strategy

| Stage | Layout |
| --- | --- |
| V1 (now) | Docs inside this repository (`docs/` + MkDocs) |
| V2 | Large models/corpora may move to a separate package |
| Later | Split `burmesenlp-docs` only if the site needs its own release cycle |

Keep docs next to the code while the public API is still moving quickly.
