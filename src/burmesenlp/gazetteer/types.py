"""Entity types for gazetteer lookup."""

from __future__ import annotations

from enum import Enum
from typing import Dict, Optional


class EntityType(Enum):
    PERSON = "PERSON"
    TOWN = "TOWN"
    VILLAGE = "VILLAGE"
    DISTRICT = "DISTRICT"
    STATE = "STATE"
    ZONE = "ZONE"
    RIVER = "RIVER"
    MOUNTAIN = "MOUNTAIN"
    ORGANIZATION = "ORGANIZATION"
    UNIVERSITY = "UNIVERSITY"
    RELIGION = "RELIGION"
    ETHNIC_GROUP = "ETHNIC_GROUP"
    HOLIDAY = "HOLIDAY"
    PAGODA = "PAGODA"


# Filename stem (without .json) → entity type
FILENAME_TO_ENTITY: Dict[str, EntityType] = {
    "male_names": EntityType.PERSON,
    "female_names": EntityType.PERSON,
    "towns": EntityType.TOWN,
    "villages": EntityType.VILLAGE,
    "districts": EntityType.DISTRICT,
    "states": EntityType.STATE,
    "self_administered_zones": EntityType.ZONE,
    "rivers": EntityType.RIVER,
    "mountains": EntityType.MOUNTAIN,
    "organizations": EntityType.ORGANIZATION,
    "universities": EntityType.UNIVERSITY,
    "religions": EntityType.RELIGION,
    "ethnic_groups": EntityType.ETHNIC_GROUP,
    "holidays": EntityType.HOLIDAY,
    "pagodas": EntityType.PAGODA,
}


def entity_type_for_filename(stem: str) -> Optional[EntityType]:
    return FILENAME_TO_ENTITY.get(stem)
