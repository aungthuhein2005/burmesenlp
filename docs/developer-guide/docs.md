# Building the documentation

Docs live in-repo under `docs/` and are built with **MkDocs Material**.

## Local preview

```bash
pip install -e ".[docs]"
mkdocs serve
```

## Build

```bash
mkdocs build --strict
```

Output: `site/` (gitignored).

## Layout

```text
docs/
  index.md
  getting-started/
  user-guide/
  algorithms/
  tutorials/
  api/              # mkdocstrings pages
  developer-guide/
  research/
  references.md
  assets/
```

API pages use `::: module.path` directives; keep public docstrings accurate.

Speed smoke (manual, not CI): see repository `benchmarks/README.md`.

## GitHub Pages

Pushing to `main` runs `.github/workflows/docs.yml`, which builds and deploys
to GitHub Pages.
