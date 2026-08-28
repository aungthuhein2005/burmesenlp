# -*- coding: utf-8 -*-
"""Empirical ambiguity/lossiness check for the zg2uni/uni2zg rule pair.

Two DIRECTIONS, run and reported SEPARATELY (they lose different things):

  DIRECTION 1 -- zg2uni on genuinely Zawgyi text (real corpus: 8 sentence
  pairs from Rabbit-Converter's own source/res/sample.json, the same
  upstream project our rule tables come from -- WTFPL, same as the rules
  already vendored). Finds Zawgyi's own under-differentiation: places
  where the cascade had to guess or where distinct Zawgyi inputs converge.
  Round trip: zg -> zg2uni -> uni2zg -> zg'. Failure = zg' != zg.

  DIRECTION 2 -- uni2zg then zg2uni on Unicode text.
    2a: myPOS v3.0 (already cached locally), a sample of real Bamar
        sentences. Round trip: uni -> uni2zg -> zg2uni -> uni'.
        Failure = uni' != uni.
    2b: real Shan/Mon Wikipedia text (already fetched this session) run
        through the SAME round trip, as a calibration check -- expected
        to fail loudly, since Zawgyi has no representation for these
        languages' letters. If it does NOT fail, that is evidence the
        lossiness accounting itself is wrong, not evidence Shan/Mon are
        safe.

For every failing sentence, the differing character span(s) (original
vs. round-tripped) are localized via difflib, then cross-referenced
against the FIRST pass's repair log (which carries origin_span in
original-text coordinates) to attribute the failure to specific rule
indices -- so failures land on rules, not just an aggregate rate.
"""
from __future__ import annotations

import difflib
import json
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, "src")

from burmesenlp.normalize import canonical_order  # noqa: E402
from burmesenlp.zawgyi.repair import _apply_rules_with_log  # noqa: E402
from burmesenlp.zawgyi.zawgyi import _uni2zg_rules, _zg2uni_rules  # noqa: E402


def _canon(s: str) -> str:
    """Same normalization convert_with_report() applies to its output:
    canonical_order() then NFC. Both matter for a fair pass/fail check --
    found empirically, not assumed:

    1. Raw string equality massively over-counts "failures" that are
       mark-ORDER artifacts canonical_order() already fixes -- e.g. asat
       and dot-below stacked on one consonant coming out in a different
       (NFC-equivalent, ccc=0-for-both) order than they went in. On a
       500-sentence myPOS sample: 113/500 raw "failures" vs 5/500 once
       canonical_order() is applied to both sides.
    2. canonical_order() alone still leaves plain NFC-precomposable pairs
       (e.g. U+1025 U+102E vs the precomposed U+1026) counted as
       failures, because canonical_order() reorders marks, it does not
       compose them. Applying NFC after canonical_order() (the exact
       pipeline the real convert_with_report() uses) is required for the
       comparison to mean what it claims to mean.
    """
    return unicodedata.normalize("NFC", canonical_order(s))


def _diff_ranges(a: str, b: str):
    """Index ranges in *a* that differ from *b* (SequenceMatcher opcodes,
    non-'equal' only)."""
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return [(i1, i2) for tag, i1, i2, _, _ in sm.get_opcodes() if tag != "equal" and i2 > i1]


def _implicated_rules(repairs, diff_ranges):
    """Rule indices from *repairs* (RepairEntry list, origin_span in the
    pre-pass original-text coordinates) whose origin_span overlaps any of
    *diff_ranges* (also original-text coordinates)."""
    hit = set()
    for r in repairs:
        s, e = r.origin_span
        for ds, de in diff_ranges:
            if s < de and ds < e:  # overlap
                hit.add(r.rule_index)
                break
    return hit


def _roundtrip(sentences, rules_pass1, rules_pass2):
    """Generic A -> pass1 -> pass2 -> A' round trip. Returns per-sentence
    results; attribution is split into two honest tiers:

    - ``first_pass_implicated``: pass-1 rules whose origin_span (original-
      text coordinates) overlaps the diff between A and A'. Precise.
    - ``second_pass_fired``: pass-2 rule indices that fired *anywhere* in
      the reconstruction, for sentences where NO pass-1 rule was
      implicated (i.e. pass 1 was a no-op on the differing region, so the
      corruption must have originated in pass 2 acting on untouched
      pass-through text). Coarser -- not position-verified against the
      original text -- and reported as a separate counter rather than
      merged into the precise one.
    """
    per_rule_first_pass = Counter()
    per_rule_second_pass_unattributed = Counter()
    n_fail = 0
    n_fail_raw = 0
    n_fail_no_first_pass_rule = 0
    examples = []
    for a in sentences:
        b, repairs1 = _apply_rules_with_log(a, rules_pass1)
        a_back, repairs2 = _apply_rules_with_log(b, rules_pass2)
        if a_back != a:
            n_fail_raw += 1
        if _canon(a_back) != _canon(a):
            n_fail += 1
            ranges = _diff_ranges(a, a_back)
            implicated = _implicated_rules(repairs1, ranges)
            if implicated:
                for idx in implicated:
                    per_rule_first_pass[idx] += 1
            else:
                n_fail_no_first_pass_rule += 1
                for idx in {r.rule_index for r in repairs2}:
                    per_rule_second_pass_unattributed[idx] += 1
            if len(examples) < 5:
                examples.append(
                    {
                        "original": a,
                        "intermediate": b,
                        "round_tripped": a_back,
                        "first_pass_implicated_rules": sorted(implicated),
                    }
                )
    return {
        "n_total": len(sentences),
        "n_fail_raw": n_fail_raw,
        "fail_rate_raw": n_fail_raw / len(sentences) if sentences else None,
        "n_fail": n_fail,
        "fail_rate": n_fail / len(sentences) if sentences else None,
        "n_fail_no_first_pass_rule": n_fail_no_first_pass_rule,
        "per_rule_first_pass_failures": dict(per_rule_first_pass),
        "per_rule_second_pass_fired_when_unattributed": dict(per_rule_second_pass_unattributed),
        "examples": examples,
    }


def roundtrip_direction1_zg2uni(zg_sentences):
    return _roundtrip(zg_sentences, _zg2uni_rules(), _uni2zg_rules())


def roundtrip_direction2_uni2zg(uni_sentences, label):
    result = _roundtrip(uni_sentences, _uni2zg_rules(), _zg2uni_rules())
    result["label"] = label
    return result


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")

    # --- Direction 1: real Zawgyi text (Rabbit-Converter's own samples) ---
    with open("research/zawgyi-repair-log/rabbit_sample.json", encoding="utf-8") as f:
        rabbit = json.load(f)
    zg_sentences = rabbit["zg"]

    print("=" * 70)
    print(f"DIRECTION 1: zg2uni on real Zawgyi text (n={len(zg_sentences)}, Rabbit-Converter sample.json)")
    print("=" * 70)
    d1 = roundtrip_direction1_zg2uni(zg_sentences)
    print(f"round-trip failures (raw string equality): {d1['n_fail_raw']}/{d1['n_total']} = {d1['fail_rate_raw']:.1%}")
    print(f"round-trip failures (after canonical_order+NFC): {d1['n_fail']}/{d1['n_total']} = {d1['fail_rate']:.1%}")
    print(f"  of which no first-pass (zg2uni) rule implicated: {d1['n_fail_no_first_pass_rule']}")
    print("first-pass per-rule failure counts (sentences implicating this rule):")
    for idx, count in sorted(d1["per_rule_first_pass_failures"].items(), key=lambda kv: -kv[1]):
        print(f"  rule {idx}: {count}")
    print("second-pass (uni2zg) rules that fired when no first-pass rule was implicated:")
    for idx, count in sorted(d1["per_rule_second_pass_fired_when_unattributed"].items(), key=lambda kv: -kv[1]):
        print(f"  rule {idx}: {count}")
    print()
    for ex in d1["examples"]:
        print("  original     :", ex["original"])
        print("  intermediate :", ex["intermediate"])
        print("  round_tripped:", ex["round_tripped"])
        print("  first-pass implicated rules:", ex["first_pass_implicated_rules"])
        print()

    # --- Direction 2a: myPOS (real Bamar Unicode, already cached) ---
    from burmesenlp.bench.corpora import load_mypos

    mypos_sentences = load_mypos(scheme="nopipe", limit=500)
    mypos_texts = ["".join(s.words) for s in mypos_sentences if s.words]

    print("=" * 70)
    print(f"DIRECTION 2a: uni2zg->zg2uni on myPOS (n={len(mypos_texts)})")
    print("=" * 70)
    d2a = roundtrip_direction2_uni2zg(mypos_texts, "myPOS")
    print(f"round-trip failures (raw string equality): {d2a['n_fail_raw']}/{d2a['n_total']} = {d2a['fail_rate_raw']:.1%}")
    print(f"round-trip failures (after canonical_order+NFC): {d2a['n_fail']}/{d2a['n_total']} = {d2a['fail_rate']:.1%}")
    print(f"  of which no first-pass (uni2zg) rule implicated: {d2a['n_fail_no_first_pass_rule']}")
    print("first-pass per-rule failure counts (top 20):")
    for idx, count in sorted(d2a["per_rule_first_pass_failures"].items(), key=lambda kv: -kv[1])[:20]:
        print(f"  rule {idx}: {count}")
    print("second-pass (zg2uni) rules that fired when no first-pass rule was implicated (top 20):")
    for idx, count in sorted(d2a["per_rule_second_pass_fired_when_unattributed"].items(), key=lambda kv: -kv[1])[:20]:
        print(f"  rule {idx}: {count}")
    print()

    # --- Direction 2b: Shan/Mon calibration check (expect loud failure) ---
    with open("research/zawgyi-repair-log/shan_bulk.txt", encoding="utf-8") as f:
        shan_text = f.read()
    with open("research/zawgyi-repair-log/mon_bulk.txt", encoding="utf-8") as f:
        mon_text = f.read()

    shan_sentences = [s for s in shan_text.replace("\n", " ").split("။") if s.strip()]
    mon_sentences = [s for s in mon_text.replace("\n", " ").split("။") if s.strip()]

    print("=" * 70)
    print(f"DIRECTION 2b: uni2zg->zg2uni on Shan (n={len(shan_sentences)}) -- expect high failure rate")
    print("=" * 70)
    d2b_shan = roundtrip_direction2_uni2zg(shan_sentences, "Shan")
    print(f"round-trip failures (raw string equality): {d2b_shan['n_fail_raw']}/{d2b_shan['n_total']} = {d2b_shan['fail_rate_raw']:.1%}")
    print(f"round-trip failures (after canonical_order+NFC): {d2b_shan['n_fail']}/{d2b_shan['n_total']} = {d2b_shan['fail_rate']:.1%}")
    print(f"  of which no first-pass (uni2zg) rule implicated: {d2b_shan['n_fail_no_first_pass_rule']}")
    print("first-pass per-rule failure counts:")
    for idx, count in sorted(d2b_shan["per_rule_first_pass_failures"].items(), key=lambda kv: -kv[1]):
        print(f"  rule {idx}: {count}")
    print("second-pass (zg2uni) rules that fired when no first-pass rule was implicated:")
    for idx, count in sorted(d2b_shan["per_rule_second_pass_fired_when_unattributed"].items(), key=lambda kv: -kv[1]):
        print(f"  rule {idx}: {count}")
    print()

    print("=" * 70)
    print(f"DIRECTION 2b: uni2zg->zg2uni on Mon (n={len(mon_sentences)}) -- expect high failure rate")
    print("=" * 70)
    d2b_mon = roundtrip_direction2_uni2zg(mon_sentences, "Mon")
    print(f"round-trip failures (raw string equality): {d2b_mon['n_fail_raw']}/{d2b_mon['n_total']} = {d2b_mon['fail_rate_raw']:.1%}")
    print(f"round-trip failures (after canonical_order+NFC): {d2b_mon['n_fail']}/{d2b_mon['n_total']} = {d2b_mon['fail_rate']:.1%}")
    print(f"  of which no first-pass (uni2zg) rule implicated: {d2b_mon['n_fail_no_first_pass_rule']}")
    print("first-pass per-rule failure counts:")
    for idx, count in sorted(d2b_mon["per_rule_first_pass_failures"].items(), key=lambda kv: -kv[1]):
        print(f"  rule {idx}: {count}")
    print("second-pass (zg2uni) rules that fired when no first-pass rule was implicated:")
    for idx, count in sorted(d2b_mon["per_rule_second_pass_fired_when_unattributed"].items(), key=lambda kv: -kv[1]):
        print(f"  rule {idx}: {count}")

    with open("research/zawgyi-repair-log/roundtrip_results.json", "w", encoding="utf-8") as f:
        json.dump(
            {"direction1": d1, "direction2a_mypos": d2a, "direction2b_shan": d2b_shan, "direction2b_mon": d2b_mon},
            f,
            ensure_ascii=False,
            indent=2,
        )
