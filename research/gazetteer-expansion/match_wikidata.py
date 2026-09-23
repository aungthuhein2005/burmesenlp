# -*- coding: utf-8 -*-
"""Confirm gazetteer-expansion candidates against Wikidata (CC0), via
chunked SPARQL bulk queries -- NOT per-candidate REST calls, which hit
Wikidata's rate limit almost immediately at this candidate count (~7300;
confirmed empirically, HTTP 429 within ~50 sequential wbsearchentities
calls).

Reads candidates-search-keys.json (myPOS-derived SEARCH KEYS ONLY -- never
shipped; see its _provenance field and burmesenlp.bench's module
docstring). Writes confirmed-matches.json: only candidates with an exact,
UNAMBIGUOUS Wikidata label/alias match, each with QID, matched label,
match kind, and confirmation date. Ambiguous candidates (matching 2+
distinct Q-items -- e.g. "China" bare label plausibly meaning the
ethnicity, the PRC, or Taiwan) are recorded separately and NOT
auto-confirmed; this file is the shipping source, not the search-key file.

Matching policy (confirmed empirically before running at scale):
  - Query both rdfs:label and skos:altLabel (UNION) -- title-prefixed
    person names and differently-phrased org names typically match only
    via alias (e.g. "Bogyoke Aung San" -> Q194161 via alias, not label).
  - Both the candidate and every returned label/alias are canonicalized
    (canonical_order(normalize(...))) before comparing -- Wikidata's
    Burmese labels are community-entered and carry the same
    encoding-variant noise as any other corpus.
  - Administrative suffixes (မြို့/တိုင်း/ပြည်နယ်/ရွာ/ခရိုင်) are stripped
    before searching -- Wikidata's place labels are consistently bare
    (ရန်ကုန် -> Q37995, not ရန်ကုန်မြို့).
  - A candidate matching more than one distinct QID (by label or alias)
    is ambiguous and is NOT auto-confirmed.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict

sys.path.insert(0, "src")

from burmesenlp.normalize import canonical_order, normalize  # noqa: E402

ADMIN_SUFFIXES = ("မြို့", "တိုင်း", "ပြည်နယ်", "ရွာ", "ခရိုင်")
USER_AGENT = "burmesenlp-research/1.0 (gazetteer expansion; see research/gazetteer-expansion/)"
CANDIDATES_PATH = "research/gazetteer-expansion/candidates-search-keys.json"
OUT_PATH = "research/gazetteer-expansion/confirmed-matches.json"
CHUNK_SIZE = 150
PAUSE_BETWEEN_CHUNKS = 1.0


def canon(s: str) -> str:
    return canonical_order(normalize(s, warn_zawgyi=False))


def strip_admin_suffix(term: str) -> "tuple[str, str]":
    for suf in ADMIN_SUFFIXES:
        if term.endswith(suf) and len(term) > len(suf):
            return term[: -len(suf)], suf
    return term, ""


def sparql_query(query: str, retries: int = 5):
    url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"}
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                return json.load(resp)
        except (urllib.error.URLError, TimeoutError, OSError, ConnectionError) as exc:
            # broad on purpose: the WDQS outage this session already hit
            # (1) a clean 429 (URLError subclass) and (2) a bare connection
            # drop with no HTTP response at all (RemoteDisconnected, which
            # is an OSError/ConnectionError, not a URLError) -- catch the
            # whole family rather than add exception types one crash at a time.
            wait = 8 * (attempt + 1)
            print(f"  query failed ({exc!r}), retrying in {wait}s...", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"SPARQL query failed after {retries} retries")


def escape_sparql_string(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def query_chunk(search_terms):
    """search_terms: list of distinct strings to look up. Returns dict
    search_term -> list of (qid, en_label, matched_text, kind)."""
    values = " ".join(f'"{escape_sparql_string(t)}"@my' for t in search_terms)
    query = f"""
    SELECT ?item ?itemLabel ?matchedLabel ?kind WHERE {{
      {{
        VALUES ?matchedLabel {{ {values} }}
        ?item rdfs:label ?matchedLabel .
        BIND("label" AS ?kind)
      }} UNION {{
        VALUES ?matchedLabel {{ {values} }}
        ?item skos:altLabel ?matchedLabel .
        BIND("alias" AS ?kind)
      }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    """
    data = sparql_query(query)
    results = defaultdict(list)
    for b in data["results"]["bindings"]:
        term = b["matchedLabel"]["value"]
        qid = b["item"]["value"].rsplit("/", 1)[-1]
        en_label = b["itemLabel"]["value"]
        kind = b["kind"]["value"]
        results[term].append((qid, en_label, term, kind))
    return results


def main():
    with open(CANDIDATES_PATH, encoding="utf-8") as f:
        payload = json.load(f)
    candidates = payload["candidates"]

    # map: search_term -> list of (original_span, count, suffix)
    search_term_sources = defaultdict(list)
    skipped = 0
    for c in candidates:
        span = c["span"]
        if len(span.strip()) < 2:
            skipped += 1
            continue
        stripped, suffix = strip_admin_suffix(span)
        search_term_sources[stripped].append((span, c["count"], suffix))

    distinct_terms = list(search_term_sources.keys())
    print(f"{len(candidates)} candidates -> {len(distinct_terms)} distinct search terms ({skipped} skipped as too short)")

    # canon(search_term) -> list of (qid, en_label, matched_text, kind)
    all_matches = {}
    n_chunks = (len(distinct_terms) + CHUNK_SIZE - 1) // CHUNK_SIZE
    for chunk_i in range(n_chunks):
        chunk = distinct_terms[chunk_i * CHUNK_SIZE : (chunk_i + 1) * CHUNK_SIZE]
        print(f"chunk {chunk_i+1}/{n_chunks} ({len(chunk)} terms)...", flush=True)
        results = query_chunk(chunk)
        # results keys are exact strings that matched -- re-key by canon()
        # of the ORIGINAL search term list (chunk), matching if any
        # returned matchedLabel canonicalizes the same as the search term
        canon_chunk = {canon(t): t for t in chunk}
        for matched_text, hits in results.items():
            c = canon(matched_text)
            if c in canon_chunk:
                orig_term = canon_chunk[c]
                all_matches.setdefault(orig_term, []).extend(hits)
        time.sleep(PAUSE_BETWEEN_CHUNKS)

    confirmed = []
    ambiguous = []
    unmatched = []
    today = time.strftime("%Y-%m-%d")

    for search_term, sources in search_term_sources.items():
        hits = all_matches.get(search_term, [])
        distinct_qids = {h[0] for h in hits}
        for span, count, suffix in sources:
            if not hits:
                unmatched.append({"span": span, "count": count})
            elif len(distinct_qids) > 1:
                ambiguous.append(
                    {
                        "span": span,
                        "count": count,
                        "search_term_used": search_term,
                        "stripped_suffix": suffix,
                        "candidates": [
                            {"wikidata_qid": qid, "wikidata_en_label": en, "matched_as": mt, "match_kind": k}
                            for qid, en, mt, k in hits
                        ],
                    }
                )
            else:
                qid, en_label, matched_as, kind = hits[0]
                confirmed.append(
                    {
                        "span": span,
                        "count": count,
                        "search_term_used": search_term,
                        "stripped_suffix": suffix,
                        "wikidata_qid": qid,
                        "wikidata_en_label": en_label,
                        "matched_as": matched_as,
                        "match_kind": kind,
                        "source": "Wikidata (CC0)",
                        "confirmed_date": today,
                    }
                )

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {"confirmed": confirmed, "ambiguous": ambiguous, "unmatched": unmatched},
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(
        f"DONE: confirmed={len(confirmed)} ambiguous={len(ambiguous)} "
        f"unmatched={len(unmatched)} skipped={skipped}"
    )


if __name__ == "__main__":
    main()
