"""Command-line interface: UTF-8 safe on every platform, including Windows."""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from ..lexicon import LexiconError
from ..pipeline import BurmeseNLP
from ..zawgyi import to_unicode, uni2zg, zg2uni

_CONVERT_MODES = frozenset({"zg2uni", "uni2zg", "to-unicode"})


def _force_utf8_stdout() -> None:
    # Windows consoles default to a legacy code page (e.g. cp1252) which
    # cannot encode Myanmar script; reconfigure when possible.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass


def main(argv: Optional[List[str]] = None) -> int:
    _force_utf8_stdout()

    parser = argparse.ArgumentParser(
        prog="burmesenlp",
        description="Myanmar (Burmese) text preprocessing: syllable/word/"
        "sentence segmentation, POS tagging, and Zawgyi/Unicode conversion.",
    )
    parser.add_argument(
        "text", nargs="*", help="Myanmar text (reads stdin when omitted)"
    )
    parser.add_argument(
        "--dictionary",
        metavar="PATH",
        help="dictionary file to merge (.json canonical, or .txt import)",
    )
    parser.add_argument(
        "--mode",
        choices=[
            "syllables",
            "words",
            "sentences",
            "pos",
            "all",
            "zg2uni",
            "uni2zg",
            "to-unicode",
        ],
        default="all",
        help="analysis or conversion mode (default: all)",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON output")
    args = parser.parse_args(argv)

    text = " ".join(args.text) if args.text else sys.stdin.read()
    if not text.strip():
        parser.error("no input text given (pass as argument or via stdin)")

    if args.mode in _CONVERT_MODES:
        if args.mode == "zg2uni":
            out: object = zg2uni(text)
        elif args.mode == "uni2zg":
            out = uni2zg(text)
        else:
            out = to_unicode(text)
        if args.json:
            print(json.dumps(out, ensure_ascii=False, indent=2))
        else:
            print(out)
        return 0

    try:
        nlp = BurmeseNLP(dictionary_path=args.dictionary)
    except LexiconError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.mode == "syllables":
        out = nlp.syllable_segment(text)
    elif args.mode == "words":
        out = nlp.word_segment(text)
    elif args.mode == "sentences":
        out = nlp.sentence_segment(text)
    elif args.mode == "pos":
        out = nlp.pos_tag(nlp.word_segment(text))
    else:
        out = nlp.process(text)

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    elif args.mode == "pos":
        for word, tag in out:  # type: ignore[union-attr]
            print(f"{word}\t{tag}")
    elif args.mode == "all":
        result = out  # type: ignore[assignment]
        print("Syllables:", " | ".join(result["syllables"]))
        print("Words:    ", " | ".join(result["words"]))
        print("Sentences:")
        for s in result["sentences"]:
            print(f"  - {s}")
        print("POS tags:")
        for word, tag in result["pos_tags"]:
            print(f"  {word}\t{tag}")
    else:
        print(" | ".join(out))  # type: ignore[arg-type]

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
