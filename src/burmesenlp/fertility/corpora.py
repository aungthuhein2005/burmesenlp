# -*- coding: utf-8 -*-
"""Corpus loaders for the fertility profiler.

myPOS (via :mod:`burmesenlp.bench.corpora`) is CC BY-NC-SA -- the same
runtime-fetch-never-vendor discipline as :mod:`burmesenlp.bench` applies,
for the same reason. Wikipedia is CC BY-SA (share-alike, no NonCommercial
restriction) -- a materially different, weaker constraint than myPOS's,
worth naming explicitly rather than lumping both under one license
warning. Neither corpus is ever vendored regardless: what ships here is
aggregate statistics (a scalar ratio, a percentile table), which cannot
reconstruct the source text the way a shipped n-gram frequency table
could -- that is the reasoning, not just precedent-matching against
bench's corpus handling.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import List, Optional

logger = logging.getLogger(__name__)

_USER_AGENT = "burmesenlp-fertility/1.0"
WIKIPEDIA_LICENSE = "CC BY-SA 4.0 -- https://creativecommons.org/licenses/by-sa/4.0/"


def _api_request(lang_code: str, params: dict, retries: int = 4) -> dict:
    url = f"https://{lang_code}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < retries - 1:
                time.sleep(8 * (attempt + 1))
                continue
            raise
    raise RuntimeError(f"unreachable: exhausted {retries} retries without returning or raising")


def fetch_wikipedia_sample(lang_code: str, n: int, *, min_chars: int = 20) -> List[str]:
    """Fetch *n* random article extracts (plain text) from
    ``<lang_code>.wikipedia.org``. Logs :data:`WIKIPEDIA_LICENSE` once.

    Not vendored anywhere: article text lives only in the caller's
    process memory / whatever the caller chooses to write to
    ``research/`` for reproducibility, never in the shipped package.
    """
    logger.warning("Wikipedia (%s) text is %s. Fetched at runtime, never vendored.", lang_code, WIKIPEDIA_LICENSE)

    data = _api_request(lang_code, {"action": "query", "list": "random", "rnnamespace": 0, "rnlimit": n, "format": "json"})
    pageids = [str(p["id"]) for p in data["query"]["random"]]

    texts = []
    for pid in pageids:
        page_data = _api_request(
            lang_code, {"action": "query", "pageids": pid, "prop": "extracts", "explaintext": 1, "format": "json"}
        )
        for page in page_data["query"]["pages"].values():
            texts.append(page.get("extract", ""))
        time.sleep(0.5)
    return [t for t in texts if len(t.strip()) >= min_chars]


def load_mypos_sentences(limit: Optional[int] = None) -> List[str]:
    """Real Burmese sentences (nopipe scheme -- matches word_tokenize()
    granularity) from myPOS, via :mod:`burmesenlp.bench.corpora` (which
    owns the actual download/cache and license logging)."""
    from ..bench.corpora import load_mypos

    sentences = load_mypos(scheme="nopipe", limit=limit)
    return ["".join(s.words) for s in sentences if s.words]


__all__ = ["fetch_wikipedia_sample", "load_mypos_sentences", "WIKIPEDIA_LICENSE"]
