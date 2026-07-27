"""Tests for gazetteer corpus + GazetteerManager."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from burmesenlp import EntityType, GazetteerHit, GazetteerManager
from burmesenlp.gazetteer.types import entity_type_for_filename
from burmesenlp.lexicon import Lexicon

GAZ_DIR = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "burmesenlp"
    / "corpus"
    / "gazetteers"
)


def test_renamed_files_exist():
    for name in (
        "districts.json",
        "ethnic_groups.json",
        "holidays.json",
        "self_administered_zones.json",
        "towns.json",
        "villages.json",
        "states.json",
        "pagodas.json",
        "metadata.json",
    ):
        assert (GAZ_DIR / name).is_file(), name


def test_entity_type_from_filename():
    assert entity_type_for_filename("towns") == EntityType.TOWN
    assert entity_type_for_filename("male_names") == EntityType.PERSON
    assert entity_type_for_filename("female_names") == EntityType.PERSON
    assert entity_type_for_filename("holidays") == EntityType.HOLIDAY
    assert entity_type_for_filename("pagodas") == EntityType.PAGODA
    assert entity_type_for_filename("metadata") is None


def test_bundled_pagodas_file_loads():
    mgr = GazetteerManager(autoload=False)
    n = mgr.load(GAZ_DIR / "pagodas.json")
    assert n >= 1
    assert (GAZ_DIR / "pagodas.json").is_file()
    # Sample entry from the corpus
    assert mgr.contains("ရွှေသာလျောင်းဘုရား")
    assert mgr.lookup("ရွှေသာလျောင်းဘုရား")[0].entity_type == EntityType.PAGODA


def test_metadata_json():
    meta = json.loads((GAZ_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert meta["version"] == "1.0"
    assert meta["license"] == "Apache-2.0"
    assert meta["language"] == "my"


@pytest.fixture
def gaz(tmp_path):
    """Small fixture gazetteer (avoid loading 14k villages in unit tests)."""
    (tmp_path / "towns.json").write_text(
        json.dumps(["ရန်ကုန်", "မန္တလေး"], ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "organizations.json").write_text(
        json.dumps(["အရန်မီးသတ်တပ်ဖွဲ့"], ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "male_names.json").write_text(
        json.dumps(["ကျော်ကျော်ထက်"], ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "female_names.json").write_text(
        json.dumps(["အောင်ဆန်းစုကြည်"], ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "holidays.json").write_text(
        json.dumps(
            {
                "holidays": [
                    {
                        "name": "လွတ်လပ်ရေးနေ့",
                        "date": "၄ ဇန်နဝါရီ",
                        "days": "၁ ရက်",
                        "remarks": "-",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (tmp_path / "metadata.json").write_text("{}", encoding="utf-8")
    return GazetteerManager(lexicon=Lexicon.default(), autoload=True, root=tmp_path)


def test_contains_and_lookup(gaz):
    assert gaz.contains("ရန်ကုန်")
    hits = gaz.lookup("ရန်ကုန်")
    assert hits
    assert hits[0].entity_type == EntityType.TOWN
    assert hits[0].attributes.get("source") == "towns"
    assert gaz.contains("ကျော်ကျော်ထက်")
    person = gaz.lookup("ကျော်ကျော်ထက်")[0]
    assert person.entity_type == EntityType.PERSON
    assert person.attributes.get("gender") == "male"
    assert person.attributes.get("source") == "male_names"


def test_person_honorific_attached_in_find_all(gaz):
    # Same tokenization as gazetteer load (ကျော်ကျော် + ထက်)
    toks = ["ဦး", "ကျော်ကျော်", "ထက်"]
    spans = gaz.find_all(toks)
    persons = [h for h in spans if h.entity_type == EntityType.PERSON]
    assert persons
    assert persons[0].tokens[0] == "ဦး"
    assert persons[0].attributes.get("gender") == "male"


def test_fused_honorific_person_match(gaz):
    """Segmenter sometimes emits ဒေါ်+name as one token."""
    spans = gaz.find_all(["ဒေါ်အောင်ဆန်းစုကြည်", "လာ", "သည်"])
    persons = [h for h in spans if h.entity_type == EntityType.PERSON]
    assert len(persons) == 1
    assert persons[0].text == "ဒေါ်အောင်ဆန်းစုကြည်"
    assert persons[0].attributes.get("gender") == "female"


def test_holiday_lookup_has_attributes(gaz):
    hits = gaz.lookup("လွတ်လပ်ရေးနေ့")
    assert hits
    assert hits[0].entity_type == EntityType.HOLIDAY
    assert hits[0].attributes.get("date") == "၄ ဇန်နဝါရီ"


def test_longest_match_and_find_all(gaz):
    from burmesenlp.mwe.loader import expression_to_tokens

    toks = list(expression_to_tokens("ရန်ကုန်", Lexicon.default()))
    hit = gaz.longest_match(toks, 0)
    assert hit is not None
    assert hit.entity_type == EntityType.TOWN
    assert hit.start == 0

    spans = gaz.find_all(toks)
    assert len(spans) == 1


def test_bundled_towns_file_loads():
    """Load a single real corpus file without full village set."""
    mgr = GazetteerManager(autoload=False)
    n = mgr.load(GAZ_DIR / "religions.json")
    assert n >= 1
    assert mgr.contains("ဗုဒ္ဓဘာသာ")
    assert mgr.lookup("ဗုဒ္ဓဘာသာ")[0].entity_type == EntityType.RELIGION


def test_public_exports():
    assert GazetteerManager is not None
    assert EntityType.TOWN.value == "TOWN"
    assert GazetteerHit is not None


def test_short_place_false_positives_need_context(tmp_path):
    """Bare 1–2 syllable place hits must not fire on common vocab (ရေး / မြင်သာ)."""
    (tmp_path / "towns.json").write_text(
        json.dumps(["ရေး", "ရန်ကုန်"], ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "villages.json").write_text(
        json.dumps(["မြင်သာ"], ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "metadata.json").write_text("{}", encoding="utf-8")
    mgr = GazetteerManager(lexicon=Lexicon.default(), autoload=True, root=tmp_path)

    # VERB readings: reject
    assert mgr.find_all(["ရေး", "သည်"], pos_tags=["VERB", "SFP"]) == []
    assert mgr.find_all(["မြင်သာ", "သည်"], pos_tags=["VERB", "SFP"]) == []

    # Locative licenses the short place reading
    hits = mgr.find_all(["ရေး", "မှာ"], pos_tags=["NOUN", "POSTP"])
    assert len(hits) == 1
    assert hits[0].entity_type == EntityType.TOWN
    assert hits[0].text == "ရေး"

    # Canonical 2-syl town with nominal POS keeps without locative
    yangon = mgr.find_all(["ရန်ကုန်", "က"], pos_tags=["NOUN", "POSTP"])
    assert len(yangon) == 1
    assert yangon[0].text == "ရန်ကုန်"
