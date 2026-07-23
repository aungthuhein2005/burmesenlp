"""Validated word lexicon (dictionary) with POS tags.

Unlike the prototype, loading errors are *raised* (``LexiconError``), never
silently swallowed, and every entry is schema-validated so malformed data
cannot corrupt downstream segmentation or tagging.

JSON (``{"word": ["tag", ...], ...}``) is the canonical storage format.
A line-based ``.txt`` import (``word\\ttag1,tag2``) is also supported for
hand-authored or spreadsheet-exported word lists; it is converted into the
same in-memory structure.  Custom files merge on top of the seed lexicon
with per-word tag union rather than replacing it.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, MutableMapping, Tuple

from .. import grammar
from ..normalize import normalize

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent / "data"

# BurmeseNLP v1 tagset (uppercase).  ABB/FW/SB/UNK kept for dictionary coverage.
POS_TAGS: Dict[str, str] = {
    "NOUN": "noun",
    "VERB": "verb",
    "ADJ": "adjective",
    "ADV": "adverb",
    "PRON": "pronoun",
    "NUM": "number (digits or text)",
    "CONJ": "conjunction",
    "INTJ": "interjection",
    "PUNCT": "punctuation",
    "POSTP": "postposition / case marker",
    "PART": "particle",
    "AUX": "auxiliary",
    "SFP": "sentence-final particle",
    "ABB": "abbreviation",
    "FW": "foreign word",
    "SB": "symbol",
    "UNK": "unknown",
}

# When a word carries several tags, they are stored in this priority order
# so that ``tags(word)[0]`` is a sensible context-free default (function
# words before content words).
TAG_PREFERENCE: Tuple[str, ...] = (
    "PUNCT", "SB", "POSTP", "SFP", "PART", "AUX", "CONJ", "PRON", "NUM",
    "ADV", "ADJ", "VERB", "NOUN", "ABB", "INTJ", "FW", "UNK",
)


class LexiconError(ValueError):
    """Raised when a lexicon file or entry is invalid."""


# ---------------------------------------------------------------------------
# Seed data (small starter lexicon; extend via JSON or Lexicon.add)
# ---------------------------------------------------------------------------

_SEED_NOUNS = (
    "မြန်မာ", "စာ", "စာပေ", "စာအုပ်", "ကျောင်း", "ကျောင်းသား", "ကျောင်းသူ",
    "အိမ်", "လမ်း", "ရေ", "နေ", "လ", "ခြင်း", "မှု", "သူ", "လူ", "ကလေး",
    "မိန်းကလေး", "ယောက်ျား", "မိန်းမ", "ခွေး", "ကြောင်", "ငှက်", "ပန်း",
    "သစ်ပင်", "နိုင်ငံ", "မြို့", "ရွာ", "ပြည်", "ခေါင်း", "လက်", "ခြေ",
    "နှလုံး", "အစာ", "ဟင်း", "ဆန်", "အသား", "ငါး", "ပေ", "ဆရာ", "ဆရာမ",
    "သွား",  # also verb "to go"; disambiguated by context rules
)
_SEED_VERBS = (
    "ဖတ်", "စား", "သောက်", "သွား", "လာ", "ကျ", "ရ", "ပြော", "ဟော", "ဖွင့်",
    "ပိတ်", "ရေး", "ဖွဲ့", "စီစဉ်", "လုပ်", "ဆောင်", "ရှိ", "ဖြစ်",
    "ပြုလုပ်", "ထား", "ယူ", "ပေး", "နေ", "စမ်း", "သပ်", "ကစား", "ခံစား",
)
_SEED_ADJECTIVES = (
    "ကြီး", "ငယ်", "လှ", "ရှည်", "တို", "ကောင်း", "ဆိုး", "မြင့်", "နိမ့်",
    "လွယ်", "ခက်", "သစ်", "ဟောင်း", "ပို",
)
_SEED_PRONOUNS = (
    "ကျွန်တော်", "ကျွန်မ", "သူ", "သူမ", "ဒီ", "ဟို", "အဲဒီ", "ဘယ်သူ",
    "ဘယ်", "အားလုံး", "ကိုယ်", "မိမိ", "ငါ", "မင်း",
)
_SEED_ADVERBS = (
    "အရမ်း", "အလွန်", "သိပ်", "တော်တော်", "မကြာခဏ", "အမြဲ", "ဘယ်တော့မှ",
    "ပို",
)
_SEED_PARTICLES = (
    "များ", "တွေ", "ပါ", "ကြ", "မ",
)
_SEED_SFP = (
    "သည်", "တယ်", "မည်", "ပြီ", "လား", "မလား", "၏",
)
_SEED_AUX = (
    "နေ", "ထား", "ခဲ့", "ပေး", "လိုက်", "ပစ်", "ဖူး",
)

# Closed-class / high-ambiguity words.  Applied as a *replace* after
# seed+JSON merge so Stage 1 always sees the full candidate set.
_CANONICAL_TAGS: Dict[str, Tuple[str, ...]] = {
    "သွား": ("VERB", "NOUN"),
    "ထား": ("VERB", "AUX"),
    "ပို": ("ADV", "ADJ"),
    "က": ("POSTP", "PART", "CONJ"),
    "သည်": ("SFP", "PART"),
    "တယ်": ("SFP", "PART"),
    "မည်": ("SFP", "PART"),
    "ပြီ": ("SFP", "PART"),
    "နေ": ("VERB", "NOUN", "AUX"),
    "မ": ("PART",),
    "အား": ("POSTP", "NOUN"),
    "နှင့်": ("POSTP", "CONJ"),
    "နဲ့": ("POSTP", "CONJ"),
    "၏": ("POSTP", "PART"),
}


def _seed_entries() -> Dict[str, set]:
    data: Dict[str, set] = {}

    def put(words: Iterable[str], tag: str) -> None:
        for w in words:
            data.setdefault(w, set()).add(tag)

    put(_SEED_NOUNS, "NOUN")
    put(_SEED_VERBS, "VERB")
    put(_SEED_ADJECTIVES, "ADJ")
    put(_SEED_PRONOUNS, "PRON")
    put(_SEED_ADVERBS, "ADV")
    put(_SEED_PARTICLES, "PART")
    put(_SEED_SFP, "SFP")
    put(_SEED_AUX, "AUX")
    put(grammar.PPM_MARKERS, "POSTP")
    put(grammar.CONJUNCTIONS, "CONJ")
    put(grammar.NUMERAL_WORDS, "NUM")
    return data


def _apply_canonical_tags(lexicon: "Lexicon") -> None:
    """Replace tags for known ambiguous/closed-class words (see ``_CANONICAL_TAGS``)."""
    for word, tags in _CANONICAL_TAGS.items():
        key = normalize(word, warn_zawgyi=False)
        lexicon._entries[key] = tuple(sorted(set(tags), key=TAG_PREFERENCE.index))
        from ..tokenize.syllable import tokenize

        lexicon._max_syllables = max(lexicon._max_syllables, len(tokenize(key)))


def _read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return f.read()
    except OSError as exc:
        raise LexiconError(f"cannot read dictionary file {path!r}: {exc}") from exc


def _parse_json_entries(path: str, text: str) -> Dict[str, List[str]]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LexiconError(f"invalid JSON in dictionary file {path!r}: {exc}") from exc
    if not isinstance(data, dict):
        raise LexiconError(
            f"dictionary root must be a JSON object, got {type(data).__name__}"
        )
    entries: Dict[str, List[str]] = {}
    for word, tags in data.items():
        if not isinstance(word, str):
            raise LexiconError(
                f"dictionary keys must be strings, got {type(word).__name__}"
            )
        if isinstance(tags, str) or not isinstance(tags, (list, tuple)):
            raise LexiconError(
                f"tags for {word!r} must be a list of tag strings, got {tags!r}"
            )
        entries[word] = list(tags)
    return entries


def _parse_txt_entries(path: str, text: str) -> Dict[str, List[str]]:
    """Parse ``word\\ttag1,tag2`` lines into a word -> tags mapping.

    Blank lines and ``#`` comments are ignored.  Tags for the same word on
    multiple lines are unioned.
    """
    entries: Dict[str, List[str]] = {}
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "\t" not in raw:
            raise LexiconError(
                f"{path!r} line {lineno}: expected 'word<TAB>tag1,tag2', "
                f"got {raw!r}"
            )
        word, _, tag_field = raw.partition("\t")
        word = word.strip()
        tags = [t.strip() for t in tag_field.split(",") if t.strip()]
        if not word:
            raise LexiconError(f"{path!r} line {lineno}: empty word")
        if not tags:
            raise LexiconError(f"{path!r} line {lineno}: word {word!r} has no POS tags")
        existing = entries.setdefault(word, [])
        for tag in tags:
            if tag not in existing:
                existing.append(tag)
    return entries


def _load_entries(path: str) -> Dict[str, List[str]]:
    """Load dictionary entries from ``.json`` (canonical) or ``.txt`` (import)."""
    ext = os.path.splitext(path)[1].lower()
    text = _read_text(path)
    if ext == ".json":
        return _parse_json_entries(path, text)
    if ext == ".txt":
        return _parse_txt_entries(path, text)
    raise LexiconError(
        f"unsupported dictionary format {ext!r} for {path!r}; "
        f"use .json (canonical) or .txt (import)"
    )


def _merge_entry_maps(
    base: MutableMapping[str, set],
    overlay: Mapping[str, Iterable[str]],
) -> None:
    """Union *overlay* tags into *base* word-by-word (in place)."""
    for word, tags in overlay.items():
        base.setdefault(word, set()).update(tags)


def _sanitize_entries(
    entries: Mapping[str, Iterable[str]],
    source: str,
) -> Dict[str, List[str]]:
    """Normalize keys and drop empty-after-normalization entries.

    Zero-width-only keys (common in scraped myPOS dumps) are skipped with a
    warning rather than aborting the whole load.  Tags for keys that collide
    after normalization are unioned.
    """
    cleaned: Dict[str, List[str]] = {}
    skipped = 0
    for word, tags in entries.items():
        key = normalize(word, warn_zawgyi=False)
        if not key:
            skipped += 1
            continue
        existing = cleaned.setdefault(key, [])
        for tag in tags:
            if tag not in existing:
                existing.append(tag)
    if skipped:
        logger.warning(
            "Skipped %d empty-after-normalization entries in %s",
            skipped,
            source,
        )
    return cleaned


class Lexicon:
    """Word -> POS-tags mapping with syllable-aware longest-match support."""

    def __init__(self, entries: Mapping[str, Iterable[str]]):
        self._entries: Dict[str, Tuple[str, ...]] = {}
        self._max_syllables = 1
        for word, tags in entries.items():
            self._insert(word, tags)

    # -- construction -------------------------------------------------------

    @classmethod
    def default(cls) -> "Lexicon":
        """Build the built-in lexicon: closed-class seed + bundled JSON files.

        Every ``lexicon/data/*.json`` file is merged (sorted by filename) onto
        the in-code seed / grammar lists so function words keep preferred
        multi-tag sets when both sources list a word.  Additional files in
        that directory are picked up automatically.
        """
        data = _seed_entries()
        json_files = sorted(_DATA_DIR.glob("*.json")) if _DATA_DIR.is_dir() else []
        if not json_files:
            logger.warning(
                "No bundled lexicon JSON under %s; using seed only",
                _DATA_DIR,
            )
            lexicon = cls(data)
            _apply_canonical_tags(lexicon)
            return lexicon

        bundled = 0
        for path in json_files:
            cleaned = _sanitize_entries(
                _parse_json_entries(str(path), _read_text(str(path))),
                path.name,
            )
            _merge_entry_maps(data, cleaned)
            bundled += len(cleaned)

        lexicon = cls(data)
        _apply_canonical_tags(lexicon)
        logger.info(
            "Loaded default lexicon from %d JSON file(s) under %s "
            "(%d bundled entries, %d total)",
            len(json_files),
            _DATA_DIR.name,
            bundled,
            len(lexicon),
        )
        return lexicon

    @classmethod
    def _from_overlay(
        cls,
        overlay: Mapping[str, Iterable[str]],
        path: str,
        *,
        merge_default: bool,
    ) -> "Lexicon":
        cleaned = _sanitize_entries(overlay, path)
        if merge_default:
            lexicon = cls.default()
            lexicon.merge(cleaned)
            logger.info(
                "Merged %d dictionary entries from %s into default lexicon "
                "(%d total)",
                len(cleaned),
                path,
                len(lexicon),
            )
        else:
            lexicon = cls(cleaned)
            logger.info("Loaded %d dictionary entries from %s", len(lexicon), path)
        return lexicon

    @classmethod
    def from_file(cls, path: str, *, merge_default: bool = False) -> "Lexicon":
        """Load a lexicon from ``.json`` or ``.txt``.

        With ``merge_default=True`` (used by :class:`BurmeseNLP`), entries are
        merged on top of :meth:`default` with per-word tag union.
        With ``merge_default=False``, only the file contents are loaded.

        Raises ``LexiconError`` on unreadable files, bad format, or schema
        violations -- never falls back silently.
        """
        return cls._from_overlay(
            _load_entries(path), path, merge_default=merge_default
        )

    @classmethod
    def from_json(cls, path: str, *, merge_default: bool = False) -> "Lexicon":
        """Load a lexicon from canonical JSON: ``{"word": ["tag", ...], ...}``.

        See :meth:`from_file` for ``merge_default`` semantics.
        """
        return cls._from_overlay(
            _parse_json_entries(path, _read_text(path)),
            path,
            merge_default=merge_default,
        )

    @classmethod
    def from_txt(cls, path: str, *, merge_default: bool = False) -> "Lexicon":
        """Load a lexicon from a line-based import file: ``word\\ttag1,tag2``.

        This is a convenience import format; :meth:`save` always writes JSON.
        See :meth:`from_file` for ``merge_default`` semantics.
        """
        return cls._from_overlay(
            _parse_txt_entries(path, _read_text(path)),
            path,
            merge_default=merge_default,
        )
    # -- mutation ------------------------------------------------------------

    def add(self, word: str, tags: Iterable[str]) -> None:
        """Add (or extend) a word with the given POS tags. O(1), no rebuild."""
        self._insert(word, tags)

    def merge(self, entries: Mapping[str, Iterable[str]]) -> None:
        """Union *entries* into this lexicon word-by-word (O(n) inserts)."""
        for word, tags in entries.items():
            self._insert(word, tags)

    def save(self, path: str) -> None:
        """Atomically save the lexicon as UTF-8 JSON (canonical format)."""
        payload = {w: list(t) for w, t in sorted(self._entries.items())}
        directory = os.path.dirname(os.path.abspath(path)) or "."
        fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    # -- lookup --------------------------------------------------------------

    def tags(self, word: str) -> Tuple[str, ...]:
        """POS tags for *word* in TAG_PREFERENCE order, or () if unknown."""
        return self._entries.get(word, ())

    @property
    def max_word_syllables(self) -> int:
        """Syllable count of the longest word (bounds longest-match search)."""
        return self._max_syllables

    def __contains__(self, word: str) -> bool:
        return word in self._entries

    def __len__(self) -> int:
        return len(self._entries)

    def words(self) -> Iterable[str]:
        return self._entries.keys()

    # -- internals -------------------------------------------------------------

    def _insert(self, word: str, tags: Iterable[str]) -> None:
        if not isinstance(word, str) or not word:
            raise LexiconError(f"dictionary word must be a non-empty string, got {word!r}")
        if any(c.isspace() for c in word):
            raise LexiconError(f"dictionary word must not contain whitespace: {word!r}")
        if isinstance(tags, str) or not isinstance(tags, (list, tuple, set, frozenset)):
            raise LexiconError(
                f"tags for {word!r} must be a list of tag strings, got {tags!r}"
            )
        tag_set = set(tags)
        if not tag_set:
            raise LexiconError(f"word {word!r} has no POS tags")
        unknown = tag_set - POS_TAGS.keys()
        if unknown:
            raise LexiconError(
                f"word {word!r} has unknown POS tags {sorted(unknown)}; "
                f"valid tags: {sorted(POS_TAGS)}"
            )

        word = normalize(word, warn_zawgyi=False)
        if not word:
            raise LexiconError(
                "dictionary word is empty after normalization "
                "(zero-width-only entries are not allowed)"
            )
        merged = set(self._entries.get(word, ())) | tag_set
        self._entries[word] = tuple(sorted(merged, key=TAG_PREFERENCE.index))
        from ..tokenize.syllable import tokenize

        self._max_syllables = max(self._max_syllables, len(tokenize(word)))
