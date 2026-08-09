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
  research/         # repo-only (excluded from the public site)
  references.md
  assets/
```

`docs/research/` (including the roadmap) stays in the repository for contributors but is
excluded from the published MkDocs site via `exclude_docs` in `mkdocs.yml`.

API pages use `::: module.path` directives; keep public docstrings accurate.

Speed smoke (manual, not CI): see repository `benchmarks/README.md`.

## GitHub Pages

Pushing to `main` runs `.github/workflows/docs.yml`, which builds and deploys
to GitHub Pages.
