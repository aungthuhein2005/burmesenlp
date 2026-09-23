# -*- coding: utf-8 -*-
"""Ship confirmed Wikidata matches to the lexicon (NOUN, for word_tokenize())
and gazetteer (entity typing; PROPN still arrives via the pipeline's
entity-lock mechanism once the gazetteer also recognizes the span).

Reads confirmed-matches.json (built by match_wikidata.py). Never reads
candidates-search-keys.json -- that file is myPOS-derived search keys
only and must never influence what's shipped, only what's searched for.

CANONICALIZE ON INGEST: every shipped string passes through
canonical_order(normalize(...)) at write time, defensively, even though
candidate spans already come from canonical_reference_text() upstream --
this is the one point a bug here would silently depress future match
rates against real text, so it's enforced here too, not just trusted.

FREQUENCY ORDER: confirmed matches are shipped in descending `count`
order (from the original myPOS disagreement frequency) -- ship the
highest-weight entries first; --limit caps the batch.

Category policy (suffix/prefix -> gazetteer file, ship form), decided
against each category's *existing* file convention, not a global rule:
  မြို့ (town)          -> towns.json,        ship bare
  ရွာ (village)         -> villages.json,     ship bare
  ခရိုင် (district)      -> districts.json,    ship WITH suffix
  တိုင်း/ပြည်နယ် (state)  -> states.json,       ship bare (majority convention)
  နိုင်ငံ (country)      -> countries.json,    ship bare (NEW category --
                                                doesn't exist yet, noted)
  တက္ကသိုလ်/ကောလိပ်/     -> universities.json, ship WITH suffix (full name)
    အကယ်ဒမီ (school)
  organization suffix   -> organizations.json, ship WITH full name (no
    (အသင်း/အဖွဲ့ချုပ်/                          stripping -- these files
    အဖွဲ့/တပ်ဖွဲ့)                                already store full formal names)
  male-coded honorific  -> male_names.json,   ship bare (strip prefix)
    (ဗိုလ်ချုပ်/ဦး/ကို/
     သခင်/ဗိုလ်)
  female-coded honorific-> female_names.json, ship bare (strip prefix)
    (ဒေါ်/မ)
  anything else          -> UNCATEGORIZED, not shipped -- flagged for
                            manual review rather than guessed.

Multi-QID ambiguous matches (see match_wikidata.py) never reach this
script at all -- they're recorded separately in confirmed-matches.json's
"ambiguous" list, not "confirmed".
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, "src")

from burmesenlp.normalize import canonical_order, normalize  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
GAZETTEER_DIR = REPO_ROOT / "src" / "burmesenlp" / "corpus" / "gazetteers"
LEXICON_PATH = REPO_ROOT / "src" / "burmesenlp" / "lexicon" / "data" / "default.json"
CONFIRMED_PATH = REPO_ROOT / "research" / "gazetteer-expansion" / "confirmed-matches.json"
SHIPPED_LOG_PATH = REPO_ROOT / "research" / "gazetteer-expansion" / "shipped-log.json"

PLACE_SUFFIXES = {
    "မြို့": ("towns", False),
    "ရွာ": ("villages", False),
    "ခရိုင်": ("districts", True),
    "တိုင်း": ("states", False),
    "ပြည်နယ်": ("states", False),
    "နိုင်ငံ": ("countries", False),
}
INSTITUTION_SUFFIXES = ("တက္ကသိုလ်", "ကောလိပ်", "အကယ်ဒမီ")
ORG_SUFFIXES = ("အသင်း", "အဖွဲ့ချုပ်", "အဖွဲ့", "တပ်ဖွဲ့")
MALE_PREFIXES = ("ဗိုလ်ချုပ်", "ဗိုလ်", "ဦး", "ကို", "သခင်")
FEMALE_PREFIXES = ("ဒေါ်", "မ")
# Gender-neutral titles: signal PERSON but not which name-file -- held for
# manual review rather than guessed.
NEUTRAL_TITLE_PREFIXES = ("ဒေါက်တာ", "ပါမောက္ခ")


def canon(s: str) -> str:
    return canonical_order(normalize(s, warn_zawgyi=False))


def classify(span: str, stripped_suffix: str) -> "tuple[str, str, str]":
    """Return (category, gazetteer_file_stem, ship_text). category is one
    of the recognized types, or "uncategorized"."""
    if stripped_suffix and stripped_suffix in PLACE_SUFFIXES:
        file_stem, keep_suffix = PLACE_SUFFIXES[stripped_suffix]
        core = span[: -len(stripped_suffix)]
        ship_text = span if keep_suffix else core
        return file_stem, file_stem, canon(ship_text)

    if span.endswith(INSTITUTION_SUFFIXES):
        return "universities", "universities", canon(span)

    if span.endswith(ORG_SUFFIXES):
        return "organizations", "organizations", canon(span)

    for p in NEUTRAL_TITLE_PREFIXES:
        if span.startswith(p):
            return "uncategorized_person_neutral_title", "", canon(span)

    for p in MALE_PREFIXES:
        if span.startswith(p) and len(span) > len(p):
            return "male_names", "male_names", canon(span[len(p) :])

    for p in FEMALE_PREFIXES:
        if span.startswith(p) and len(span) > len(p):
            return "female_names", "female_names", canon(span[len(p) :])

    return "uncategorized", "", canon(span)


def load_confirmed(limit: Optional[int] = None) -> List[dict]:
    with open(CONFIRMED_PATH, encoding="utf-8") as f:
        data = json.load(f)
    confirmed = sorted(data["confirmed"], key=lambda c: -c["count"])
    if limit is not None:
        confirmed = confirmed[:limit]
    return confirmed


def build_batch(confirmed: List[dict]) -> dict:
    """Classify every confirmed match; return
    {file_stem: [ship_text, ...], "uncategorized": [...], "lexicon_entries": [...]}."""
    by_file: "dict[str, list]" = {}
    uncategorized = []
    lexicon_entries = []
    audit = []

    for c in confirmed:
        category, file_stem, ship_text = classify(c["span"], c.get("stripped_suffix", ""))
        entry_record = {
            "ship_text": ship_text,
            "category": category,
            "original_span": c["span"],
            "count": c["count"],
            "wikidata_qid": c["wikidata_qid"],
            "wikidata_en_label": c["wikidata_en_label"],
            "match_kind": c["match_kind"],
            "source": c["source"],
            "confirmed_date": c["confirmed_date"],
        }
        audit.append(entry_record)

        if not file_stem:
            uncategorized.append(entry_record)
            continue

        by_file.setdefault(file_stem, [])
        if ship_text not in by_file[file_stem]:
            by_file[file_stem].append(ship_text)
        if ship_text not in lexicon_entries:
            lexicon_entries.append(ship_text)

    return {"by_file": by_file, "uncategorized": uncategorized, "lexicon_entries": lexicon_entries, "audit": audit}


def write_gazetteer_files(by_file: dict, batch_date: str) -> List[str]:
    """One new file per category, named so it's physically separate from
    the original bundled data (auditable provenance) -- NOT merged into
    the existing towns.json/etc. Registers the new stem with the loader
    via _SOURCE_ATTRS / FILENAME_TO_ENTITY (see accompanying manual step
    -- this script writes data files; the entity-type/source registration
    lines to add to gazetteer/types.py and gazetteer/manager.py are
    printed, not auto-edited, since that's source code, not data)."""
    written = []
    for file_stem, entries in by_file.items():
        out_name = f"{file_stem}_wikidata_{batch_date}.json"
        out_path = GAZETTEER_DIR / out_name
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(sorted(entries), f, ensure_ascii=False, indent=2)
        written.append(out_name)
    return written


def write_lexicon_entries(lexicon_entries: List[str]) -> int:
    with open(LEXICON_PATH, encoding="utf-8") as f:
        lexicon = json.load(f)
    added = 0
    for entry in lexicon_entries:
        if entry not in lexicon:
            lexicon[entry] = ["NOUN"]
            added += 1
    with open(LEXICON_PATH, "w", encoding="utf-8") as f:
        json.dump(lexicon, f, ensure_ascii=False, indent=0, sort_keys=True)
    return added


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="ship only the top-N by frequency")
    parser.add_argument("--dry-run", action="store_true", help="classify and report, write nothing")
    args = parser.parse_args()

    confirmed = load_confirmed(limit=args.limit)
    print(f"loaded {len(confirmed)} confirmed matches (frequency order, limit={args.limit})")

    batch = build_batch(confirmed)
    print(f"categorized: {len(batch['audit']) - len(batch['uncategorized'])} categorized, "
          f"{len(batch['uncategorized'])} uncategorized (not shipped)")
    for stem, entries in batch["by_file"].items():
        print(f"  {stem}: {len(entries)} entries")
    print(f"lexicon: {len(batch['lexicon_entries'])} distinct NOUN entries to add")

    if args.dry_run:
        print("--dry-run: nothing written")
        return

    batch_date = time.strftime("%Y-%m-%d")
    written_gaz_files = write_gazetteer_files(batch["by_file"], batch_date)
    added_lexicon = write_lexicon_entries(batch["lexicon_entries"])

    log_entry = {
        "batch_date": batch_date,
        "n_confirmed_shipped": len(confirmed) - len(batch["uncategorized"]),
        "n_uncategorized": len(batch["uncategorized"]),
        "gazetteer_files_written": written_gaz_files,
        "lexicon_entries_added": added_lexicon,
        "audit": batch["audit"],
    }
    prior_log = []
    if SHIPPED_LOG_PATH.exists():
        prior_log = json.loads(SHIPPED_LOG_PATH.read_text(encoding="utf-8"))
    prior_log.append(log_entry)
    SHIPPED_LOG_PATH.write_text(json.dumps(prior_log, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nWrote gazetteer files: {written_gaz_files}")
    print(f"Added {added_lexicon} lexicon entries")
    print(f"Logged to {SHIPPED_LOG_PATH}")
    print(
        "\nMANUAL STEP required: register the new gazetteer file stems in "
        "src/burmesenlp/gazetteer/types.py (FILENAME_TO_ENTITY) and "
        "src/burmesenlp/gazetteer/manager.py (_SOURCE_ATTRS) -- this script "
        "writes data files only, not source code."
    )


if __name__ == "__main__":
    main()
