"""``--diff`` mode: show specific disagreement spans against another
segmenter's output, not just aggregate scores.

This module cannot run myWord or mmCRFseg itself -- neither ships as an
installable package burmesenlp can call into, and downloading/executing
third-party tool binaries at runtime is out of scope here. Instead it
diffs against a *pre-computed* segmentation file you supply (one
sentence per line, space-separated words, in the same sentence order as
the gold corpus) -- produced by running that tool yourself.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Sequence

from .boundaries import canonical_reference_text, word_boundaries


def load_external_segmentation(path: str) -> List[List[str]]:
    """One sentence per line, words space-separated (a common convention
    for segmenter output, e.g. myWord's)."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [line.split() for line in lines if line.strip()]


def diff_spans(
    reference_text: str,
    words_a: Sequence[str],
    words_b: Sequence[str],
    label_a: str,
    label_b: str,
) -> List[str]:
    """Return human-readable lines for each span where two segmentations
    of the *same* reference_text disagree on a boundary."""
    b_a = word_boundaries(words_a)
    b_b = word_boundaries(words_b)
    only_a = sorted(b_a - b_b)
    only_b = sorted(b_b - b_a)
    if not only_a and not only_b:
        return []

    lines = [f"  text: {reference_text}"]
    for pos in only_a:
        ctx = reference_text[max(0, pos - 8) : pos] + "[" + label_a + "]" + reference_text[pos : pos + 8]
        lines.append(f"    only {label_a} splits here: ...{ctx}...")
    for pos in only_b:
        ctx = reference_text[max(0, pos - 8) : pos] + "[" + label_b + "]" + reference_text[pos : pos + 8]
        lines.append(f"    only {label_b} splits here: ...{ctx}...")
    return lines


def run_diff(
    gold_word_lists: Sequence[Sequence[str]],
    our_segment_fn,
    external_path: str,
    external_name: str,
    max_sentences: int = 50,
) -> str:
    external = load_external_segmentation(external_path)
    if len(external) != len(gold_word_lists):
        raise ValueError(
            f"external segmentation has {len(external)} lines but gold has "
            f"{len(gold_word_lists)} sentences -- must be line-aligned to the "
            f"same corpus/scheme you are scoring"
        )

    out_lines = [f"--diff: burmesenlp vs {external_name}"]
    shown = 0
    disagreeing_sentences = 0
    for gold_words, ext_words in zip(gold_word_lists, external):
        if shown >= max_sentences:
            break
        reference_text = canonical_reference_text(gold_words)
        our_words = our_segment_fn(reference_text)
        spans = diff_spans(reference_text, our_words, ext_words, "burmesenlp", external_name)
        if spans:
            disagreeing_sentences += 1
            out_lines.append(f"[{disagreeing_sentences}]")
            out_lines.extend(spans)
            shown += 1

    out_lines.append(
        f"\n{disagreeing_sentences} disagreeing sentences shown "
        f"(capped at {max_sentences}) out of {len(gold_word_lists)} total"
    )
    return "\n".join(out_lines)
