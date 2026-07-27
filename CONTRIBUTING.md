# Contributing to BurmeseNLP

Thanks for helping improve BurmeseNLP. Version 1 is a **rule-based** toolkit.
Please keep contributions aligned with that scope.

## Development setup

```bash
git clone https://github.com/aungthuhein2005/burmesenlp.git
cd burmesenlp
python -m pip install -e ".[dev]"
```

Documentation site (MkDocs Material):

```bash
pip install -e ".[docs]"
mkdocs serve
```

## Checks before opening a PR

```bash
ruff check src tests
mypy src/burmesenlp
pytest
```

Optional packaging smoke (builds a wheel and installs into a temp venv):

```bash
# Unix
BURMESENLP_PACKAGING_TEST=1 pytest -m packaging

# Windows PowerShell
$env:BURMESENLP_PACKAGING_TEST = "1"; pytest -m packaging
```

CI runs the same checks on every push and pull request.

## Version bumps

When releasing, update **all three** together:

1. `src/burmesenlp/__init__.py` → `__version__`
2. `pyproject.toml` → `version`
3. `CHANGELOG.md` → new section



## What belongs in V1 PRs

- Bug fixes for normalize / tokenize / tag / Zawgyi / lexicon
- Documentation and packaging improvements
- Golden / regression tests with real Burmese text
- Lexicon quality (validated JSON/txt merges)



## What does not belong in V1 PRs

Do **not** add unfinished public features for:

- CRF / Transformers / embeddings
- NER, sentiment, spell checking
- SentencePiece  / new tokenization algorithms
- Heavy ML dependencies

Architecture hooks under `models/` and placeholder trees under `corpus/`
exist for later versions — do not advertise them as working V1 features.

## Pull requests

- Keep diffs focused; match existing style.
- Add or update tests for behavior changes.
- Be respectful; follow the [Code of Conduct](CODE_OF_CONDUCT.md).



## License

By contributing, you agree that your contributions are licensed under the
Apache License 2.0 (see [LICENSE](LICENSE)).