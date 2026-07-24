#!/usr/bin/env python3
"""Speed smoke for BurmeseNLP.process() — not a gold-standard accuracy bench.

Usage (from repo root)::

    python benchmarks/speed_smoke.py
    python benchmarks/speed_smoke.py --repeat 50
"""

from __future__ import annotations

import argparse
import time

# Fixed Unicode Burmese samples (no Zawgyi). Keep short and stable.
SAMPLES = [
    "မင်္ဂလာပါ။",
    "ကျွန်တော်ကျောင်းသို့သွားသည်။",
    "သူသည် ကျောင်းကို သွားသည်။",
    "မင်္ဂလာပါ။ ကျွန်တော်တို့သည် မြန်မာဘာသာစကားကို လေ့လာနေကြသည်။",
    "စာပေကိုဖတ်သည်။သူကစားသည်။",
    "ကျွန်တော် မန္တလေးကို မနေ့က သွားခဲ့တယ်။",
    "ဒီကောင် အိတ်ပေါက်နှင့် ဖားကောက် နေတာပါကွာ။",
    "ခွေးနှင့်ကြောင်ကိုမြင်သည်။",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repeat",
        type=int,
        default=20,
        help="How many times to process the full sample list (default: 20)",
    )
    args = parser.parse_args()
    if args.repeat < 1:
        raise SystemExit("--repeat must be >= 1")

    from burmesenlp import BurmeseNLP

    nlp = BurmeseNLP()
    # Warm-up (lexicon + idioms + grammar load)
    for text in SAMPLES:
        nlp.process(text)

    n = len(SAMPLES) * args.repeat
    t0 = time.perf_counter()
    for _ in range(args.repeat):
        for text in SAMPLES:
            nlp.process(text)
    elapsed = time.perf_counter() - t0
    rate = n / elapsed if elapsed > 0 else float("inf")
    print(
        f"sentences={n} repeat={args.repeat} "
        f"elapsed_s={elapsed:.3f} sentences_per_sec={rate:.1f}"
    )


if __name__ == "__main__":
    main()
