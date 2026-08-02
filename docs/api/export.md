# Export

Span-based corpus export for training datasets. Converts pipeline
``Document`` objects without changing the parser or ``Document`` API.

```python
from burmesenlp import process, CorpusExporter

doc = process("ကျွန်တော်ကျောင်းသို့သွားသည်။")
exporter = CorpusExporter()

exporter.to_json(doc)       # {"sentences": [...]}
exporter.to_jsonl(doc)      # one JSON object per sentence
exporter.to_conll(doc)
exporter.to_brat(doc)       # {"txt": ..., "ann": ...}
exporter.to_labelstudio(doc)
```

::: burmesenlp.export.CorpusExporter

::: burmesenlp.export.CorpusImporter

::: burmesenlp.export.SentenceRecord

::: burmesenlp.export.TokenRecord

::: burmesenlp.export.ChunkRecord

::: burmesenlp.export.ClauseRecord

::: burmesenlp.export.EntityRecord

::: burmesenlp.export.MWERecord
