# -*- coding: utf-8 -*-
"""Measure the OLD is_zawgyi() heuristic's false-positive rate on genuine
Shan and Mon Wikipedia text (real corpora, not synthetic), and the ported
bigram detector's rate on the same text for contrast.

Karen: no live Wikipedia edition exists for any Karen variety (ksw/kjp
checked directly -- both unresolvable), and a quick eBible lookup did not
turn up a fetchable id either. Not measured here; see the note passed back
to the user rather than substituting a different corpus silently.

Every document fetched is real Wikipedia article text (public domain/CC
BY-SA per Wikipedia's terms), used here transiently for measurement only
-- nothing is vendored into the package.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, "src")
sys.path.insert(0, "research/zawgyi-repair-log")

from burmesenlp.zawgyi import is_zawgyi  # noqa: E402
from detector_prototype import ZawgyiDetector  # noqa: E402

USER_AGENT = "burmesenlp-research/1.0 (zawgyi FPR measurement)"


def fetch_random_articles(lang_code: str, n: int) -> list:
    """Fetch n random article extracts (plain text) from <lang_code>.wikipedia.org."""
    base = f"https://{lang_code}.wikipedia.org/w/api.php"
    req = urllib.request.Request(
        base + "?" + urllib.parse.urlencode(
            {"action": "query", "list": "random", "rnnamespace": 0, "rnlimit": n, "format": "json"}
        ),
        headers={"User-Agent": USER_AGENT},
    )
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.load(resp)
            break
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < 4:
                time.sleep(10 * (attempt + 1))
                continue
            raise
    pageids = [str(p["id"]) for p in data["query"]["random"]]

    # prop=extracts silently caps at ~1 page's worth of content per request
    # for anonymous multi-pageid requests regardless of exlimit -- fetch
    # one page per request instead (slower, but reliable).
    texts = []
    for pid in pageids:
        req2 = urllib.request.Request(
            base + "?" + urllib.parse.urlencode(
                {
                    "action": "query",
                    "pageids": pid,
                    "prop": "extracts",
                    "explaintext": 1,
                    "format": "json",
                }
            ),
            headers={"User-Agent": USER_AGENT},
        )
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req2, timeout=30) as resp:
                    data2 = json.load(resp)
                break
            except urllib.error.HTTPError as exc:
                if exc.code == 429 and attempt < 3:
                    time.sleep(10 * (attempt + 1))
                    continue
                raise
        pages = data2["query"]["pages"]
        for p in pages.values():
            texts.append(p.get("extract", ""))
        time.sleep(1.0)
    return [t for t in texts if len(t.strip()) > 20]


def measure(lang_code: str, lang_name: str, n: int, det: ZawgyiDetector):
    articles = fetch_random_articles(lang_code, n)
    print(f"\n=== {lang_name} ({lang_code}.wikipedia.org): {len(articles)} articles fetched ===")

    # document-level
    doc_old_fp = sum(1 for a in articles if is_zawgyi(a))
    doc_new_fp = sum(1 for a in articles if det.get_zawgyi_probability(a) > 0.5)
    print(f"  document-level:  old is_zawgyi() false-positive rate = {doc_old_fp}/{len(articles)} = {doc_old_fp/len(articles):.1%}")
    print(f"                   new bigram detector (>0.5)          = {doc_new_fp}/{len(articles)} = {doc_new_fp/len(articles):.1%}")

    # paragraph-level (matches the granularity the new feature will actually use)
    paragraphs = []
    for a in articles:
        paragraphs.extend(p for p in a.split("\n") if len(p.strip()) > 5)
    para_old_fp = sum(1 for p in paragraphs if is_zawgyi(p))
    para_new_fp = sum(1 for p in paragraphs if det.get_zawgyi_probability(p) > 0.5)
    print(f"  paragraph-level: old is_zawgyi() false-positive rate = {para_old_fp}/{len(paragraphs)} = {para_old_fp/len(paragraphs):.1%}  (n={len(paragraphs)} paragraphs)")
    print(f"                   new bigram detector (>0.5)          = {para_new_fp}/{len(paragraphs)} = {para_new_fp/len(paragraphs):.1%}")

    return {
        "lang": lang_code,
        "n_articles": len(articles),
        "n_paragraphs": len(paragraphs),
        "doc_old_fp_rate": doc_old_fp / len(articles),
        "doc_new_fp_rate": doc_new_fp / len(articles),
        "para_old_fp_rate": para_old_fp / len(paragraphs),
        "para_new_fp_rate": para_new_fp / len(paragraphs),
    }


if __name__ == "__main__":
    det = ZawgyiDetector("research/zawgyi-repair-log/zawgyiUnicodeModel.dat")
    results = {}
    for code, name in [("shn", "Shan"), ("mnw", "Mon")]:
        results[code] = measure(code, name, 25, det)

    with open("research/zawgyi-repair-log/fpr_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
