"""Load MWE resources (JSON string arrays or line-based TXT) into a trie.

Token boundaries always come from the same pipeline word tokenizer
(normalize → syllable tokenize → longest-match word segment).  Spaces in
corpus strings are ignored (skipped like at runtime), so spacing variants
of an idiom collapse to one token sequence.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..lexicon import Lexicon
from ..normalize import normalize
from ..tokenize.longest import WordSegmenter
from ..tokenize.syllable import tokenize
from .models import MWEEntry
from .trie import MWETrie

logger = logging.getLogger(__name__)

_CACHE_VERSION = 1

_CATEGORY_HINTS: Tuple[Tuple[str, str], ...] = (
    ("idiom", "IDIOM"),
    ("organization", "ORGANIZATION"),
    ("org", "ORGANIZATION"),
    ("location", "LOCATION"),
    ("person", "PERSON"),
)


def infer_category(path: str, override: Optional[str] = None) -> str:
    if override:
        return override
    lowered = path.replace("\\", "/").lower()
    for hint, category in _CATEGORY_HINTS:
        if hint in lowered:
            return category
    return "MWE"


def expression_to_tokens(
    text: str,
    lexicon: Lexicon,
    *,
    segmenter: Optional[WordSegmenter] = None,
) -> Tuple[str, ...]:
    """Normalize *text* and word-tokenize with the pipeline segmenter.

    Whitespace is not a token boundary authoring rule — the syllable
    tokenizer skips it, so spaced and unspaced idiom strings yield the
    same sequence when the lexicon is unchanged.
    """
    norm = normalize(text, warn_zawgyi=False)
    if not norm:
        return ()
    seg = segmenter if segmenter is not None else WordSegmenter(lexicon)
    return tuple(t.text for t in seg.segment(tokenize(norm)))


def _read_expressions(path: Path) -> List[str]:
    raw = path.read_text(encoding="utf-8-sig")
    ext = path.suffix.lower()
    if ext == ".json":
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError(f"MWE JSON root must be a list, got {type(data).__name__}")
        out: List[str] = []
        for item in data:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
            elif isinstance(item, dict) and "text" in item:
                t = item.get("text")
                if isinstance(t, str) and t.strip():
                    out.append(t.strip())
        return out
    out = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def _content_fingerprint(path: Path) -> str:
    """Stable content hash (survives checkout mtime changes)."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:32]


def _lexicon_fingerprint(lexicon: Lexicon) -> str:
    """Fingerprint bundled lexicon data that drives word segmentation."""
    del lexicon  # API hook; fingerprint is from on-disk default data
    data_dir = Path(__file__).resolve().parent.parent / "lexicon" / "data"
    if not data_dir.is_dir():
        return "no-lexicon-data"
    h = hashlib.sha256()
    for p in sorted(data_dir.glob("*.json")):
        h.update(p.name.encode("utf-8"))
        h.update(b"\0")
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    return h.hexdigest()[:32]


def cache_path_for(source: Path) -> Path:
    """``idioms.json`` → ``idioms.cache.json`` (same directory)."""
    return source.with_name(source.stem + ".cache.json")


def _entries_from_cache_payload(
    data: Dict[str, Any],
    *,
    category: str,
    priority: int,
    allow_unigrams: bool,
) -> Optional[List[MWEEntry]]:
    raw_entries = data.get("entries")
    if not isinstance(raw_entries, list):
        return None
    by_tokens: Dict[Tuple[str, ...], MWEEntry] = {}
    for item in raw_entries:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        tokens = item.get("tokens")
        if not isinstance(text, str) or not isinstance(tokens, list):
            continue
        if not all(isinstance(t, str) for t in tokens):
            continue
        tok_t = tuple(tokens)
        if not tok_t:
            continue
        if len(tok_t) < 2 and not allow_unigrams:
            continue
        pri = int(item.get("priority", priority))
        entry = MWEEntry(
            text=text,
            tokens=tok_t,
            category=str(item.get("category", category)),
            priority=pri,
            pos=item.get("pos") if isinstance(item.get("pos"), str) else None,
        )
        prev = by_tokens.get(tok_t)
        if prev is None or entry.priority >= prev.priority:
            by_tokens[tok_t] = entry
    return list(by_tokens.values())


def try_load_cache(
    source: Path,
    lexicon: Lexicon,
    *,
    category: str,
    priority: int = 0,
    allow_unigrams: bool = False,
    cache_file: Optional[Path] = None,
) -> Optional[List[MWEEntry]]:
    """Return entries from cache if present and fresh; else ``None``."""
    cpath = cache_file or cache_path_for(source)
    if not cpath.is_file() or not source.is_file():
        return None
    try:
        data = json.loads(cpath.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.debug("Ignoring unreadable MWE cache %s: %s", cpath, exc)
        return None
    if not isinstance(data, dict):
        return None
    if data.get("version") != _CACHE_VERSION:
        return None
    if data.get("source_fingerprint") != _content_fingerprint(source):
        return None
    if data.get("lexicon_fingerprint") != _lexicon_fingerprint(lexicon):
        return None
    entries = _entries_from_cache_payload(
        data,
        category=category,
        priority=priority,
        allow_unigrams=allow_unigrams,
    )
    if entries is None:
        return None
    logger.info("Loaded %d MWE entries from cache %s", len(entries), cpath)
    return entries


def build_cache_payload(
    source: Path,
    entries: List[MWEEntry],
    lexicon: Lexicon,
) -> Dict[str, Any]:
    return {
        "version": _CACHE_VERSION,
        "source": source.name,
        "source_fingerprint": _content_fingerprint(source),
        "lexicon_fingerprint": _lexicon_fingerprint(lexicon),
        "entries": [
            {
                "text": e.text,
                "tokens": list(e.tokens),
                "category": e.category,
                "priority": e.priority,
                **({"pos": e.pos} if e.pos else {}),
            }
            for e in entries
        ],
    }


def write_cache(
    source: Path,
    entries: List[MWEEntry],
    lexicon: Lexicon,
    *,
    cache_file: Optional[Path] = None,
) -> Optional[Path]:
    """Write tokenized cache beside *source* (or *cache_file*). Best-effort."""
    cpath = cache_file or cache_path_for(source)
    payload = build_cache_payload(source, entries, lexicon)
    try:
        cpath.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        logger.info("Wrote MWE cache (%d entries) → %s", len(entries), cpath)
        return cpath
    except OSError as exc:
        logger.debug("Could not write MWE cache to %s: %s", cpath, exc)
        return None


def tokenize_expressions(
    expressions: List[str],
    lexicon: Lexicon,
    *,
    category: str,
    priority: int = 0,
    allow_unigrams: bool = False,
) -> List[MWEEntry]:
    """Tokenize expression strings with the pipeline word segmenter."""
    segmenter = WordSegmenter(lexicon)
    by_tokens: Dict[Tuple[str, ...], MWEEntry] = {}
    skipped = 0
    for expr in expressions:
        tokens = expression_to_tokens(expr, lexicon, segmenter=segmenter)
        if not tokens:
            skipped += 1
            continue
        if len(tokens) < 2 and not allow_unigrams:
            skipped += 1
            continue
        entry = MWEEntry(
            text=expr, tokens=tokens, category=category, priority=priority
        )
        prev = by_tokens.get(tokens)
        if prev is None or entry.priority >= prev.priority:
            by_tokens[tokens] = entry
    if skipped:
        logger.debug("Skipped %d empty/unigram MWE rows", skipped)
    return list(by_tokens.values())


def load_entries(
    path: str,
    lexicon: Lexicon,
    *,
    category: Optional[str] = None,
    priority: int = 0,
    allow_unigrams: bool = False,
    use_cache: bool = True,
    write_cache_on_miss: bool = True,
) -> List[MWEEntry]:
    """Load and tokenize expressions from *path* into ``MWEEntry`` objects."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"MWE resource not found: {path}")
    cat = infer_category(str(p), category)

    if use_cache:
        cached = try_load_cache(
            p,
            lexicon,
            category=cat,
            priority=priority,
            allow_unigrams=allow_unigrams,
        )
        if cached is not None:
            return cached

    expressions = _read_expressions(p)
    entries = tokenize_expressions(
        expressions,
        lexicon,
        category=cat,
        priority=priority,
        allow_unigrams=allow_unigrams,
    )

    if write_cache_on_miss:
        write_cache(p, entries, lexicon)

    return entries


def load_into_trie(
    trie: MWETrie,
    path: str,
    lexicon: Lexicon,
    *,
    category: Optional[str] = None,
    priority: int = 0,
    allow_unigrams: bool = False,
    use_cache: bool = True,
    write_cache_on_miss: bool = True,
) -> int:
    """Load a resource file into *trie*; return number of entries inserted."""
    entries = load_entries(
        path,
        lexicon,
        category=category,
        priority=priority,
        allow_unigrams=allow_unigrams,
        use_cache=use_cache,
        write_cache_on_miss=write_cache_on_miss,
    )
    for entry in entries:
        trie.insert(entry)
    return len(entries)


def default_idioms_path() -> Optional[str]:
    path = Path(__file__).resolve().parent.parent / "corpus" / "idioms" / "idioms.json"
    return str(path) if path.is_file() else None
