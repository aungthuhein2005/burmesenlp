# Installation

## From PyPI

```bash
pip install burmesenlp
```

Requires **Python 3.9+**. Runtime depends only on **PyYAML** (phrase grammar).

### Optional: `engine="xlmr"` POS tagger

```bash
pip install "burmesenlp[xlmr]"
```

Pulls in `transformers`/`torch` for the XLM-RoBERTa POS engine (see
[POS tagging](../user-guide/pos.md#alternate-engine-enginexlmr)). Not
required for the default `engine="rule"` pipeline.

## From source (development)

```bash
git clone https://github.com/aungthuhein2005/burmesenlp.git
cd burmesenlp
pip install -e ".[dev]"
```

### Docs extras

To build this site locally:

```bash
pip install -e ".[docs]"
mkdocs serve
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Verify

```python
import burmesenlp
print(burmesenlp.__version__)
```
