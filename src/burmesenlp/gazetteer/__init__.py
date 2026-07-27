"""Gazetteer lookup (rule-based entity lists)."""

from .manager import GazetteerManager
from .models import GazetteerHit
from .types import FILENAME_TO_ENTITY, EntityType, entity_type_for_filename

__all__ = [
    "EntityType",
    "FILENAME_TO_ENTITY",
    "GazetteerHit",
    "GazetteerManager",
    "entity_type_for_filename",
]
