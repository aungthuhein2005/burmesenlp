"""GazetteerManager: load string-list gazetteers into a shared token trie."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

from ..lexicon import Lexicon
from ..mwe.loader import expression_to_tokens
from ..structures.token_trie import TokenTrie
from ..tokenize.syllable import tokenize as syllable_tokenize
from .models import GazetteerHit
from .types import EntityType, entity_type_for_filename

logger = logging.getLogger(__name__)

_GAZETTEER_DIR = (
    Path(__file__).resolve().parent.parent / "corpus" / "gazetteers"
)

# Geographic types where short surfaces collide with common vocabulary
# (ရေး TOWN, မြင်သာ VILLAGE, …).
_PLACE_TYPES = frozenset(
    {
        EntityType.TOWN,
        EntityType.VILLAGE,
        EntityType.DISTRICT,
        EntityType.STATE,
        EntityType.ZONE,
        EntityType.RIVER,
        EntityType.MOUNTAIN,
    }
)

# Locative / admin cues that license a short place reading nearby.
_LOCATIVE_CUES = frozenset(
    {
        "မှာ",
        "တွင်",
        "၌",
        "သို့",
        "မှ",
        "မြို့",
        "ရွာ",
        "ခရိုင်",
        "တိုင်း",
        "ပြည်နယ်",
        "မြို့နယ်",
        "ကျေးရွာ",
    }
)

# POS tags that block a bare short place match (unless locative context).
_NON_PLACE_POS = frozenset(
    {"VERB", "ADJ", "ADV", "AUX", "PART", "SFP", "CONJ", "POSTP"}
)


class GazetteerManager:
    """Load gazetteer JSON files and provide contains / lookup / match APIs.

    Used by ``BurmeseNLP.process()`` (after POS) to fill ``Document.entities``.
    First full load tokenizes every surface (including large village lists)
    and may take noticeable time; pass ``gazetteer=False`` to skip.
    """

    def __init__(
        self,
        lexicon: Optional[Lexicon] = None,
        *,
        autoload: bool = True,
        root: Optional[Path] = None,
    ):
        self._lexicon = lexicon if lexicon is not None else Lexicon.default()
        self._root = Path(root) if root is not None else _GAZETTEER_DIR
        self._trie: TokenTrie[GazetteerHit] = TokenTrie()
        self._by_norm: Dict[str, List[GazetteerHit]] = {}
        self._holiday_attrs: Dict[str, Dict] = {}
        self._count = 0
        if autoload and self._root.is_dir():
            self.load(self._root)

    def __len__(self) -> int:
        return self._count

    def load(self, path: Optional[Union[Path, str]] = None) -> int:
        """Load a gazetteer directory or a single JSON file. Returns entries added."""
        target = Path(path) if path is not None else self._root
        if target.is_file():
            return self._load_file(target)
        if not target.is_dir():
            raise FileNotFoundError(f"Gazetteer path not found: {target}")
        added = 0
        for fp in sorted(target.glob("*.json")):
            if fp.name == "metadata.json":
                continue
            added += self._load_file(fp)
        return added

    def _load_file(self, path: Path) -> int:
        stem = path.stem
        etype = entity_type_for_filename(stem)
        if etype is None:
            logger.debug("Skipping unrecognized gazetteer file %s", path.name)
            return 0
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
        if etype == EntityType.HOLIDAY:
            return self._load_holidays(raw, etype)
        if not isinstance(raw, list):
            raise ValueError(f"{path.name}: expected JSON array of strings")
        n = 0
        base_attrs = _source_attributes(stem)
        for item in raw:
            if not isinstance(item, str) or not item.strip():
                continue
            n += self._insert_surface(
                item.strip(), etype, attributes=dict(base_attrs)
            )
        return n

    def _load_holidays(self, raw: object, etype: EntityType) -> int:
        if not isinstance(raw, dict):
            raise ValueError("holidays.json: expected object with 'holidays' list")
        items = raw.get("holidays") or []
        if not isinstance(items, list):
            raise ValueError("holidays.json: 'holidays' must be a list")
        n = 0
        for obj in items:
            if not isinstance(obj, dict):
                continue
            name = obj.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            name = name.strip()
            attrs = {
                "date": obj.get("date"),
                "days": obj.get("days"),
                "remarks": obj.get("remarks"),
                "source": "holidays",
            }
            self._holiday_attrs[name] = attrs
            n += self._insert_surface(name, etype, attributes=attrs)
        return n

    def _insert_surface(
        self,
        text: str,
        etype: EntityType,
        *,
        attributes: Optional[Dict] = None,
    ) -> int:
        tokens = expression_to_tokens(text, self._lexicon)
        if not tokens:
            return 0
        hit = GazetteerHit(
            text=text,
            tokens=tokens,
            entity_type=etype,
            attributes=dict(attributes or {}),
        )
        self._trie.insert(tokens, hit)
        key = "".join(tokens)
        self._by_norm.setdefault(key, []).append(hit)
        # Also index original stripped text without spaces for contains()
        compact = "".join(text.split())
        if compact and compact != key:
            self._by_norm.setdefault(compact, []).append(hit)
        self._count += 1
        return 1

    def _normalize_query(self, text: str) -> Tuple[str, Tuple[str, ...]]:
        tokens = expression_to_tokens(text, self._lexicon)
        return "".join(tokens), tokens

    def contains(self, text: str) -> bool:
        key, _ = self._normalize_query(text)
        if key in self._by_norm:
            return True
        compact = "".join(text.split())
        return compact in self._by_norm

    def lookup(self, text: str) -> List[GazetteerHit]:
        key, _ = self._normalize_query(text)
        hits = list(self._by_norm.get(key, []))
        if not hits:
            compact = "".join(text.split())
            hits = list(self._by_norm.get(compact, []))
        # Enrich holidays from side map if needed
        out: List[GazetteerHit] = []
        for h in hits:
            if h.entity_type == EntityType.HOLIDAY and not h.attributes:
                attrs = self._holiday_attrs.get(h.text, {})
                out.append(
                    GazetteerHit(
                        text=h.text,
                        tokens=h.tokens,
                        entity_type=h.entity_type,
                        start=h.start,
                        end=h.end,
                        attributes=dict(attrs),
                    )
                )
            else:
                out.append(h)
        return out

    def longest_match(
        self,
        tokens: Sequence[str],
        start: int = 0,
    ) -> Optional[GazetteerHit]:
        """Longest trie hit starting at *start*, or None."""
        hits = self._trie.search(tokens, start)
        if not hits:
            return None
        best = max(hits, key=lambda h: len(h.tokens))
        end = start + len(best.tokens) - 1
        return GazetteerHit(
            text=best.text,
            tokens=best.tokens,
            entity_type=best.entity_type,
            start=start,
            end=end,
            attributes=dict(best.attributes),
        )

    def find_all(
        self,
        tokens: Sequence[str],
        *,
        pos_tags: Optional[Sequence[str]] = None,
    ) -> List[GazetteerHit]:
        """Greedy left-to-right longest matches over *tokens*.

        PERSON hits absorb a preceding honorific token when present
        (``ဦး`` / ``ဒေါ်`` / …). Also matches a single token that fuses
        honorific + name (``ဒေါ်အောင်ဆန်းစုကြည်``).

        Short geographic hits (1–2 syllables) are rejected unless a locative
        cue is nearby, or — for 2-syllable names — the span's POS looks
        nominal. Pass post-BMWE ``pos_tags`` aligned with *tokens*.
        """
        tags = list(pos_tags) if pos_tags is not None else None
        if tags is not None and len(tags) != len(tokens):
            raise ValueError(
                f"tokens/pos_tags length mismatch: {len(tokens)} != {len(tags)}"
            )
        out: List[GazetteerHit] = []
        i = 0
        n = len(tokens)
        while i < n:
            hit = self.longest_match(tokens, i)
            if hit is None:
                hit = self._match_fused_person_honorific(tokens, i)
            if hit is None:
                i += 1
                continue
            if hit.entity_type == EntityType.PERSON:
                hit = _maybe_attach_honorific(tokens, hit)
            if not _accept_hit(hit, tokens, tags):
                # Do not consume the span — try a longer start next token.
                i += 1
                continue
            out.append(hit)
            i = hit.end + 1
        return out

    def _match_fused_person_honorific(
        self,
        tokens: Sequence[str],
        start: int,
    ) -> Optional[GazetteerHit]:
        """Match ``ဒေါ်``+name fused into one word token."""
        if start >= len(tokens):
            return None
        word = tokens[start]
        for hon in sorted(_PERSON_HONORIFICS, key=len, reverse=True):
            if not word.startswith(hon) or len(word) <= len(hon):
                continue
            rest = word[len(hon) :]
            key, _rest_toks = self._normalize_query(rest)
            hits = list(self._by_norm.get(key, []))
            if not hits:
                hits = list(self._by_norm.get(rest, []))
            for h in hits:
                if h.entity_type != EntityType.PERSON:
                    continue
                return GazetteerHit(
                    text=word,
                    tokens=(word,),
                    entity_type=EntityType.PERSON,
                    start=start,
                    end=start,
                    attributes=dict(h.attributes),
                )
        return None


# Filename → metadata attached to every surface from that file
_SOURCE_ATTRS: Dict[str, Dict] = {
    "male_names": {"gender": "male", "source": "male_names"},
    "female_names": {"gender": "female", "source": "female_names"},
    "towns": {"source": "towns"},
    "villages": {"source": "villages"},
    "districts": {"source": "districts"},
    "states": {"source": "states"},
    "self_administered_zones": {"source": "self_administered_zones"},
    "rivers": {"source": "rivers"},
    "mountains": {"source": "mountains"},
    "organizations": {"source": "organizations"},
    "universities": {"source": "universities"},
    "religions": {"source": "religions"},
    "ethnic_groups": {"source": "ethnic_groups"},
    "pagodas": {"source": "pagodas"},
}

# Person title tokens that may precede a gazetteer PERSON name
_PERSON_HONORIFICS = frozenset(
    {
        "ဦး",
        "ဒေါ်",
        "မောင်",
        "ရှင်",
        "ဆရာ",
        "ဆရာမ",
    }
)


def _source_attributes(stem: str) -> Dict:
    return dict(_SOURCE_ATTRS.get(stem, {"source": stem}))


def _maybe_attach_honorific(
    tokens: Sequence[str], hit: GazetteerHit
) -> GazetteerHit:
    """Extend a PERSON hit one token left when that token is an honorific."""
    if hit.entity_type != EntityType.PERSON or hit.start <= 0:
        return hit
    prev = tokens[hit.start - 1]
    if prev not in _PERSON_HONORIFICS:
        return hit
    new_start = hit.start - 1
    new_tokens = (prev,) + tuple(hit.tokens)
    return GazetteerHit(
        text="".join(new_tokens),
        tokens=new_tokens,
        entity_type=hit.entity_type,
        start=new_start,
        end=hit.end,
        attributes=dict(hit.attributes),
    )


def _syllable_count(text: str) -> int:
    return len(syllable_tokenize(text))


def _has_locative_context(
    tokens: Sequence[str],
    hit: GazetteerHit,
    *,
    window: int = 3,
) -> bool:
    lo = max(0, hit.start - window)
    hi = min(len(tokens), hit.end + 1 + window)
    for j in range(lo, hi):
        if hit.start <= j <= hit.end:
            continue
        if tokens[j] in _LOCATIVE_CUES:
            return True
    return False


_EMBEDDABLE_TYPES = frozenset({EntityType.RELIGION, EntityType.ETHNIC_GROUP})


def _is_embedded_in_noun_compound(
    hit: GazetteerHit,
    tokens: Sequence[str],
    tags: Optional[Sequence[str]],
) -> bool:
    """True if hit is flanked by NOUNs with no boundary — i.e. it's a
    modifier inside a longer compound (e.g. ဗုဒ္ဓဘာသာ inside
    ...ဗုဒ္ဓဘာသာအထက်တန်းကျောင်း), not a standalone entity mention.
    """
    if tags is None:
        return False
    left = hit.start - 1
    right = hit.end + 1
    has_left_noun = left >= 0 and left < len(tags) and tags[left] == "NOUN"
    has_right_noun = right < len(tags) and tags[right] == "NOUN"
    return has_left_noun and has_right_noun


def _accept_hit(
    hit: GazetteerHit,
    tokens: Sequence[str],
    tags: Optional[Sequence[str]],
) -> bool:
    """Filter false-positive short place-name matches."""
    # Reject religion/ethnic-group hits swallowed inside a longer compound
    # noun (modifier position), regardless of length — these aren't
    # standalone mentions.
    if hit.entity_type in _EMBEDDABLE_TYPES:
        if _is_embedded_in_noun_compound(hit, tokens, tags):
            return False

    if hit.entity_type not in _PLACE_TYPES:
        return True
    surface = "".join(hit.tokens)
    syl = _syllable_count(surface)
    # Longer place names are specific enough without extra checks.
    if syl > 2:
        return True
    if _has_locative_context(tokens, hit):
        return True
    # Bare 1-syllable places (ရေး) are almost always vocabulary collisions.
    if syl <= 1:
        return False
    # 2-syllable: keep only when POS looks nominal (ရန်ကုန် NOUN vs မြင်သာ VERB).
    if tags is not None:
        for i in range(hit.start, hit.end + 1):
            if i < len(tags) and tags[i] in _NON_PLACE_POS:
                return False
    return True