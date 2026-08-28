"""``burmesenlp bench`` -- boundary-level word-segmentation evaluation."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from .. import __version__
from ..gazetteer import GazetteerManager
from ..mwe import BMWEEngine
from ..normalize import canonical_order, normalize
from ..pipeline import BurmeseNLP
from ..tokenize.syllable import tokenize as syllable_tokenize
from .audit import categorize, find_disagreements, sample_diverse
from .boundaries import score_corpus, score_corpus_stratified
from .corpora import ALT_LICENSE, MYPOS_LICENSE, collapse_stats, load_alt, load_mypos
from .diff import run_diff


def _canon(word: str) -> str:
    return canonical_order(normalize(word, warn_zawgyi=False))


def _header(
    *,
    corpus: str,
    scheme: str,
    n: int,
    stages: str,
    license_: str,
    collapse: "tuple[int, int, int]",
) -> str:
    raw, canon, collapsed = collapse
    pct = 100 * collapsed / raw if raw else 0.0
    lines = [
        "=" * 70,
        f"corpus:   {corpus}",
        f"scheme:   {scheme}",
        f"n:        {n} sentences",
        f"pipeline: {stages}",
        f"license:  {license_} (fetched at runtime, not vendored)",
        f"canonicalization: {collapsed}/{raw} raw gold word-forms collapsed "
        f"({pct:.2f}%) -- see burmesenlp.normalize.canonical_order",
        "=" * 70,
    ]
    return "\n".join(lines)


def _run_scheme(
    scheme: str,
    limit: Optional[int],
    diff_arg: Optional[str],
    max_diff: int,
    category: bool = False,
) -> int:
    sentences = load_mypos(scheme=scheme, limit=limit)
    gold_word_lists = [s.words for s in sentences]
    collapse = collapse_stats(sentences)

    nlp = BurmeseNLP(gazetteer=False)

    if scheme == "nopipe":
        stages = "normalize -> syllables -> word_tokenize (alone)"

        def segment_fn(text: str) -> List[str]:
            return nlp.word_segment(text)

    else:
        stages = "normalize -> syllables -> word_tokenize -> BMWE"
        mwe = BMWEEngine(lexicon=nlp.lexicon)

        def segment_fn(text: str) -> List[str]:
            return mwe.process(nlp.word_segment(text))

    print(
        _header(
            corpus="myPOS v3.0",
            scheme=scheme,
            n=len(gold_word_lists),
            stages=stages,
            license_=MYPOS_LICENSE,
            collapse=collapse,
        )
    )

    if scheme == "pipe":
        print()
        print(
            "Required check before trusting this F1: BMWE's compound "
            "inventory and myPOS's `|` convention were built "
            "independently and may disagree about what counts as one "
            "compound. Sampling disagreements..."
        )
        disagreements = find_disagreements(
            gold_word_lists,
            nlp.word_segment,
            segment_fn,
        )
        distinct_sentences = len({d.sentence_index for d in disagreements})
        crossing_punct = sum(1 for d in disagreements if d.crosses_punctuation)
        sample = sample_diverse(disagreements, n=20)
        print(
            f"Found {len(disagreements)} disagreement positions across "
            f"{distinct_sentences} distinct sentences "
            f"({100*crossing_punct/max(1,len(disagreements)):.1f}% span punctuation -- "
            f"a strong tell they are not lexical compounds at all). "
            f"Showing up to 20, spread across distinct sentences:"
        )
        for i, d in enumerate(sample, 1):
            flag = " [spans punctuation]" if d.crosses_punctuation else ""
            print(f"  [{i}] sent#{d.sentence_index} ({d.direction}){flag} ...{d.span_text}...")
        print(
            f"({len(sample)} shown / {len(disagreements)} total -- judge each by "
            f"eye: real segmentation error vs. definitional difference between "
            f"BMWE's trie and myPOS's compound convention. This harness cannot "
            f"make that call automatically.)"
        )
        print()

        if category:
            print(
                "--category: heuristic triage, not authoritative -- a starting "
                "point matching what a skim of the audit output would also flag. "
                "proper_noun relies on the gazetteer's OWN coverage, so a known "
                "gazetteer gap (e.g. a place/org name it doesn't have yet) falls "
                "through to genuine_compound here too; that's the toolkit's gap, "
                "not this categorizer's."
            )
            gaz = GazetteerManager(lexicon=nlp.lexicon, autoload=True)

            def is_proper_noun(span: str) -> bool:
                toks = [t.text for t in syllable_tokenize(span)]
                return bool(gaz.find_all(toks))

            buckets: "dict[str, list]" = {
                "date_number": [],
                "productive_derivation": [],
                "proper_noun": [],
                "genuine_compound": [],
            }
            for d in disagreements:
                buckets[categorize(d, is_proper_noun)].append(d)

            print("Category breakdown (work queue for growing BMWE's trie):")
            for cat, items in buckets.items():
                print(f"  {cat}: {len(items)} positions")
            genuine = buckets["genuine_compound"]
            print(
                f"\n{len(genuine)} in genuine_compound -- a narrower fallback "
                f"bucket (everything not caught by the other three heuristics), "
                f"not a confirmed-real count. It still contains definitional "
                f"cases the heuristics miss (e.g. a span crossing a grammatical "
                f"particle like ကို/၏/သို့/နှင့်), so this is the work queue to "
                f"skim, not a ready-made bug list. Sample of up to 20, spread "
                f"across distinct sentences:"
            )
            for i, d in enumerate(sample_diverse(genuine, n=20), 1):
                print(f"  [{i}] sent#{d.sentence_index} {d.compound_text!r}")
            print()

    counts, detail = score_corpus(gold_word_lists, segment_fn)
    print(
        f"precision={counts.precision:.4f}  recall={counts.recall:.4f}  "
        f"f1={counts.f1:.4f}  (tp={counts.tp} fp={counts.fp} fn={counts.fn})"
    )

    if scheme == "nopipe":
        gold_word_forms = {_canon(w) for words in gold_word_lists for w in words}
        in_lexicon_forms = {w for w in gold_word_forms if w in nlp.lexicon}
        print()
        print(
            "CAUTION -- possible train-on-test: the bundled lexicon's word-form "
            "inventory is derived from myPOS (100% of the lexicon's ~24k word-forms "
            "appear in myPOS v3.0's gold vocabulary). The aggregate score above "
            "measures how well greedy longest-match recovers the corpus its own "
            "dictionary came from, not general Burmese segmentation ability. Read "
            "the OOV-stratum numbers below as the honest generalization estimate."
        )
        print(
            f"lexicon coverage of myPOS gold word-form types: "
            f"{len(in_lexicon_forms)}/{len(gold_word_forms)} "
            f"({100*len(in_lexicon_forms)/max(1,len(gold_word_forms)):.2f}%)"
        )
        strat = score_corpus_stratified(gold_word_lists, segment_fn, lambda w: w in nlp.lexicon)
        print(
            f"  in-lexicon boundaries: precision={strat.iv.precision:.4f}  "
            f"recall={strat.iv.recall:.4f}  f1={strat.iv.f1:.4f}  "
            f"(tp={strat.iv.tp} fp={strat.iv.fp} fn={strat.iv.fn})"
        )
        print(
            f"  OOV boundaries:        precision={strat.oov.precision:.4f}  "
            f"recall={strat.oov.recall:.4f}  f1={strat.oov.f1:.4f}  "
            f"(tp={strat.oov.tp} fp={strat.oov.fp} fn={strat.oov.fn})"
        )
        print()

    if diff_arg:
        if "=" not in diff_arg:
            print("--diff expects name=path", file=sys.stderr)
            return 2
        name, path = diff_arg.split("=", 1)
        print()
        print(run_diff(gold_word_lists, segment_fn, path, name, max_sentences=max_diff))

    return 0


def _run_alt(limit: Optional[int], diff_arg: Optional[str], max_diff: int) -> int:
    sentences = load_alt(limit=limit)
    gold_word_lists = [s.words for s in sentences]
    collapse = collapse_stats(sentences)

    nlp = BurmeseNLP(gazetteer=False)

    def segment_fn(text: str) -> List[str]:
        return nlp.word_segment(text)

    print(
        _header(
            corpus="Myanmar ALT (Asian Language Treebank)",
            scheme="ALT-uni-pos",
            n=len(gold_word_lists),
            stages="normalize -> syllables -> word_tokenize (alone)",
            license_=ALT_LICENSE,
            collapse=collapse,
        )
    )
    print(
        "Independent of myPOS: different corpus (Wikinews translations, "
        "not Wikipedia), different word scheme (ALT's own Uni-POS "
        "convention, not myPOS's). This score is not train-on-test "
        "against the bundled lexicon in the way the myPOS score is -- "
        "see the myPOS in-lexicon/OOV stratified numbers for that "
        "comparison."
    )

    counts, detail = score_corpus(gold_word_lists, segment_fn)
    print(
        f"precision={counts.precision:.4f}  recall={counts.recall:.4f}  "
        f"f1={counts.f1:.4f}  (tp={counts.tp} fp={counts.fp} fn={counts.fn})"
    )

    if diff_arg:
        if "=" not in diff_arg:
            print("--diff expects name=path", file=sys.stderr)
            return 2
        name, path = diff_arg.split("=", 1)
        print()
        print(run_diff(gold_word_lists, segment_fn, path, name, max_sentences=max_diff))

    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="burmesenlp bench",
        description="Boundary-level P/R/F1 for burmesenlp word segmentation "
        "against gold corpora (myPOS v3.0; CC BY-NC-SA, fetched at runtime).",
    )
    parser.add_argument(
        "--corpus",
        choices=["mypos", "alt"],
        default="mypos",
        help="mypos (default): CC BY-NC-SA, and the bundled lexicon's "
        "vocabulary is derived from it -- see the train-on-test caution "
        "printed with nopipe scores. alt: Myanmar ALT (CC BY-NC-SA), an "
        "independent corpus and word scheme, not implicated in that "
        "contamination.",
    )
    parser.add_argument(
        "--scheme",
        choices=["nopipe", "pipe", "both"],
        default="nopipe",
        help="myPOS only. nopipe: score word_tokenize() alone (default). "
        "pipe: score word_tokenize()+BMWE against compound-preserving gold. "
        "both: run both and report separately.",
    )
    parser.add_argument("--limit", type=int, default=None, help="cap sentence count (for quick runs)")
    parser.add_argument(
        "--diff",
        metavar="NAME=PATH",
        default=None,
        help="compare against a pre-computed external segmentation file "
        "(one sentence per line, space-separated words, line-aligned to "
        "the gold corpus) -- e.g. --diff myword=myword_output.txt",
    )
    parser.add_argument("--max-diff", type=int, default=50, help="max disagreeing sentences to print for --diff")
    parser.add_argument(
        "--category",
        action="store_true",
        help="pipe scheme only: bucket disagreements into date_number / "
        "productive_derivation / proper_noun / genuine_compound, turning "
        "the audit into a work queue for growing BMWE's trie.",
    )
    parser.add_argument("--version", action="version", version=f"burmesenlp {__version__}")
    args = parser.parse_args(argv)

    if args.corpus == "alt":
        return _run_alt(args.limit, args.diff, args.max_diff)

    schemes = ["nopipe", "pipe"] if args.scheme == "both" else [args.scheme]
    for i, scheme in enumerate(schemes):
        if i:
            print()
        rc = _run_scheme(scheme, args.limit, args.diff, args.max_diff, args.category)
        if rc:
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
