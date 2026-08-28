# -*- coding: utf-8 -*-
"""``burmesenlp fertility`` -- token-fertility profiler CLI."""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from .backends import TOKENIZER_NAMES, load_backend
from .corpora import fetch_wikipedia_sample, load_mypos_sentences
from .measure import (
    CAVEAT_BASELINE_COMPARABLE_NOT_PARALLEL,
    CAVEAT_PER_RUN_OVERSTATES_TOTAL,
    WORD_SCHEME,
    aggregate_distribution,
    measure_text,
)

_RATIO_KEYS = ("tokens_per_byte", "tokens_per_char", "tokens_per_syllable", "tokens_per_word")


def _load_corpus(name: str, n: int) -> List[str]:
    if name == "mypos":
        return load_mypos_sentences(limit=n)
    if name == "wikipedia-my":
        return fetch_wikipedia_sample("my", n)
    if name == "wikipedia-en":
        return fetch_wikipedia_sample("en", n)
    raise ValueError(f"unknown corpus {name!r}; choose from mypos, wikipedia-my, wikipedia-en")


def _run(args: argparse.Namespace) -> int:
    tokenizer_names = args.tokenizers.split(",") if args.tokenizers else list(TOKENIZER_NAMES)
    for name in tokenizer_names:
        if name not in TOKENIZER_NAMES:
            print(f"error: unknown tokenizer {name!r}; choose from {TOKENIZER_NAMES}", file=sys.stderr)
            return 2

    print(f"loading tokenizer backends: {', '.join(tokenizer_names)} ...", file=sys.stderr)
    backends = {name: load_backend(name) for name in tokenizer_names}

    print(f"word denominator scheme: {WORD_SCHEME}")
    print(f"caveat: {CAVEAT_PER_RUN_OVERSTATES_TOTAL}")
    print(f"caveat: {CAVEAT_BASELINE_COMPARABLE_NOT_PARALLEL}")
    print()

    texts = _load_corpus(args.corpus, args.n)
    print(f"corpus={args.corpus} n_documents={len(texts)}")

    results = [measure_text(t, backends, canonicalize=not args.no_canonicalize) for t in texts]

    report = {
        "corpus": args.corpus,
        "n_documents": len(texts),
        "word_scheme": WORD_SCHEME,
        "caveats": [CAVEAT_PER_RUN_OVERSTATES_TOTAL, CAVEAT_BASELINE_COMPARABLE_NOT_PARALLEL],
        "distributions": {},
    }
    for tok_name in tokenizer_names:
        report["distributions"][tok_name] = {}
        print(f"\n=== {tok_name} ===")
        for ratio_key in _RATIO_KEYS:
            dist = aggregate_distribution(results, tok_name, ratio_key)
            report["distributions"][tok_name][ratio_key] = dist
            if dist["n"]:
                print(
                    f"  {ratio_key:20s} n={dist['n']:5d}  mean={dist['mean']:.3f}  "
                    f"min={dist['min']:.3f}  p10={dist['p10']:.3f}  median={dist['median']:.3f}  "
                    f"p90={dist['p90']:.3f}  max={dist['max']:.3f}  spread={dist['spread']:.3f}"
                )

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\nwrote {args.json}", file=sys.stderr)

    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="burmesenlp fertility", description="Token-fertility profiler")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="measure fertility over a corpus")
    run_p.add_argument("--corpus", choices=["mypos", "wikipedia-my", "wikipedia-en"], required=True)
    run_p.add_argument("--tokenizers", default=None, help=f"comma-separated, default all: {','.join(TOKENIZER_NAMES)}")
    run_p.add_argument("--n", type=int, default=50, help="number of documents/sentences to sample")
    run_p.add_argument("--no-canonicalize", action="store_true", help="skip canonical_order()+NFC (measures encoding noise too -- for comparison only)")
    run_p.add_argument("--json", default=None, help="write full report (with caveats) to this JSON path")
    run_p.set_defaults(func=_run)

    ns = parser.parse_args(argv)
    return ns.func(ns)


if __name__ == "__main__":
    raise SystemExit(main())
