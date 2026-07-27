# Phrase & clause chunking

YAML-driven shallow chunker: **maximal munch** (longer span wins; priority
breaks ties), then entity locks as NP. Clause types come from
`clause_rules.yml` via `ClauseParser`, not from `phrase_rules.yml`.

```python
from burmesenlp import BurmeseNLP, ClauseType

nlp = BurmeseNLP()
doc = nlp.process("မိုးရွာလျှင်အိမ်မှာနေမည်။")

for sent in doc.sentence_trees:
    for clause in sent.clauses:
        print(clause.type, clause.text)
        for phr in clause.phrases:
            print(" ", phr.type, phr.text, phr.semantic_role)
```

## Pipeline order

```
POS → Phrase chunking → Sentence segmentation → Clause parsing
```

`ClauseParser` consumes **phrase chunks** (plus markers from YAML), never
raw words alone. Relative constructions nest inside NP.

## Hierarchy

```
Document
 └── SyntaxSentence          # doc.sentence_trees
       └── Clause            # MAIN | CONDITIONAL | …
             └── Phrase      # NP / VP / PP / …
                   └── children   # RelativeModifier + HeadNoun
```

Flat `doc.chunks` remain phrase spans for backward compatibility.

## Clause types (V1)

| Type | Markers (see YAML) |
| --- | --- |
| `MAIN` | end markers / remainder with VP |
| `CONDITIONAL` | `လျှင်`, `ရင်`, `လျှင်မူ` |
| `REASON` | `ကြောင့်`, `သဖြင့်`, … |
| `PURPOSE` | `ရန်`, `အောင်`, `ဖို့` (requires NP before VP) |
| `CONTRAST` | `သော်လည်း`, `သော်`, … |
| `RELATIVE` | nested in NP only (`သော`, `တဲ့`, …) |

Bare `VP + ရန်` becomes a **Purpose VP** (`role=PurposeVP`), not a PURPOSE clause.

## Grammar files

Under `src/burmesenlp/corpus/grammar/`:

- `phrase_rules.yml` / `phrase_markers.yml` / `phrase_exceptions.yml`
- `clause_rules.yml` — markers + phrase patterns
- `postposition_roles.yml` — default semantic roles for PPs (V1 assigns default only)
