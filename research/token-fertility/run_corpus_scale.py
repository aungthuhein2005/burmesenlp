# -*- coding: utf-8 -*-
"""Corpus-scale token-fertility run. Not part of the shipped package --
lives in research/ like the gazetteer-expansion and zawgyi-repair-log
work. Produces aggregate distributions only (mean/percentiles/min/max),
never raw corpus text, into fertility_results.json.
"""
from __future__ import annotations

import json
import sys

sys.path.insert(0, "src")

from burmesenlp.fertility.backends import TOKENIZER_NAMES, load_backend  # noqa: E402
from burmesenlp.fertility.corpora import fetch_wikipedia_sample, load_mypos_sentences  # noqa: E402
from burmesenlp.fertility.measure import aggregate_distribution, measure_text  # noqa: E402

RATIO_KEYS = ("tokens_per_byte", "tokens_per_char", "tokens_per_syllable", "tokens_per_word")

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")

    print("loading tokenizer backends...")
    backends = {name: load_backend(name) for name in TOKENIZER_NAMES}

    print("loading corpora...")
    mypos_texts = load_mypos_sentences(limit=200)
    my_wiki_texts = fetch_wikipedia_sample("my", 50)
    en_wiki_texts = fetch_wikipedia_sample("en", 50)

    print(f"myPOS: {len(mypos_texts)} sentences")
    print(f"Burmese Wikipedia: {len(my_wiki_texts)} articles")
    print(f"English Wikipedia: {len(en_wiki_texts)} articles")

    corpora = {
        "mypos": mypos_texts,
        "wikipedia-my": my_wiki_texts,
        "wikipedia-en": en_wiki_texts,
    }

    report = {}
    for corpus_name, texts in corpora.items():
        print(f"\nmeasuring {corpus_name} ({len(texts)} documents)...")
        results = [measure_text(t, backends) for t in texts]
        report[corpus_name] = {"n_documents": len(texts), "distributions": {}}
        for tok_name in TOKENIZER_NAMES:
            report[corpus_name]["distributions"][tok_name] = {
                ratio_key: aggregate_distribution(results, tok_name, ratio_key) for ratio_key in RATIO_KEYS
            }
        # keep the FertilityResult objects around for cross-corpus ratio
        # computation below (mean-of-per-doc-tokens/-per-doc-denominator,
        # NOT ratio-of-corpus-totals -- see writeup)
        report[corpus_name]["_results"] = results

    print("\n" + "=" * 70)
    print("SUMMARY: mean tokens/word and tokens/byte per tokenizer per corpus")
    print("=" * 70)
    for corpus_name in corpora:
        print(f"\n{corpus_name}:")
        for tok_name in TOKENIZER_NAMES:
            d = report[corpus_name]["distributions"][tok_name]
            print(
                f"  {tok_name:12s} tok/word: mean={d['tokens_per_word']['mean']:.3f} "
                f"median={d['tokens_per_word']['median']:.3f} p90={d['tokens_per_word']['p90']:.3f} "
                f"max={d['tokens_per_word']['max']:.3f}  |  "
                f"tok/byte: mean={d['tokens_per_byte']['mean']:.3f} median={d['tokens_per_byte']['median']:.3f}"
            )

    print("\n" + "=" * 70)
    print("Burmese-vs-English ratio (mean tok/word, mean tok/byte), per tokenizer")
    print("=" * 70)
    for tok_name in TOKENIZER_NAMES:
        my_word = report["wikipedia-my"]["distributions"][tok_name]["tokens_per_word"]["mean"]
        en_word = report["wikipedia-en"]["distributions"][tok_name]["tokens_per_word"]["mean"]
        my_byte = report["wikipedia-my"]["distributions"][tok_name]["tokens_per_byte"]["mean"]
        en_byte = report["wikipedia-en"]["distributions"][tok_name]["tokens_per_byte"]["mean"]
        print(
            f"  {tok_name:12s} word ratio (my/en) = {my_word/en_word:.2f}x   "
            f"byte ratio (my/en) = {my_byte/en_byte:.2f}x"
        )

    # strip non-serializable _results before dumping
    serializable = {
        k: {"n_documents": v["n_documents"], "distributions": v["distributions"]} for k, v in report.items()
    }
    with open("research/token-fertility/fertility_results.json", "w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)
    print("\nwrote research/token-fertility/fertility_results.json")
