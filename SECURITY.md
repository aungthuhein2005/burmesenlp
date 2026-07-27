# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 1.x | Yes |
| versions before 1.0 | No |

## Reporting a vulnerability

Please report security issues in **library code** (e.g. unsafe deserialization,
path traversal in loaders, dependency risks) privately:

1. Prefer [GitHub Security Advisories](https://github.com/aungthuhein2005/burmesenlp/security/advisories/new) for this repository, or
2. Open a private report via the repository’s Security tab if advisories are enabled.

Do **not** open a public issue for exploitable vulnerabilities until a fix is available.

We aim to acknowledge reports within a reasonable time and to coordinate disclosure after a patch or mitigation is ready.

## Out of scope

The following are **not** treated as security vulnerabilities:

- Incorrect linguistic output (tokenization, POS, chunks, idioms)
- Heuristic Zawgyi detection false positives/negatives
- Missing dictionary coverage or rule gaps

File those as ordinary bugs or enhancement requests.
