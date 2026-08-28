"""Gold corpus loaders for :mod:`burmesenlp.bench`.

Every corpus here is CC BY-NC-SA (NonCommercial) or stricter. None is
vendored: each loader downloads to :func:`burmesenlp.bench.cache.corpus_cache_dir`
on first use and logs the license every time, since this constraint is
easy to forget once a corpus is sitting quietly in a cache directory.

myPOS v3.0 ships two word-boundary schemes in the *same* corpus, not just
across corpora:

- ``nopipe``: compound words are flattened -- a compound's parts are
  indistinguishable from independent words. Matches the granularity of
  ``word_tokenize()`` alone (compound/idiom merging is the separate,
  later BMWE stage, not part of word segmentation).
- ``pipe``: compound sub-parts are joined with the corpus's own ``|``
  marker (see myPOS's README, word-segmentation rule 6) and are merged
  here into one gold token with no internal boundary -- the
  compound-preserving scheme, for scoring ``word_tokenize()`` + BMWE
  together.

These are genuinely different gold standards; :mod:`burmesenlp.bench`
never mixes scores across them without saying so in the output header.
"""

from __future__ import annotations

import logging
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence

from .cache import corpus_cache_dir

logger = logging.getLogger(__name__)

MYPOS_LICENSE = "CC BY-NC-SA 4.0 (NonCommercial) -- https://creativecommons.org/licenses/by-nc-sa/4.0/"
MYPOS_SOURCE = "https://github.com/ye-kyaw-thu/myPOS"

_MYPOS_URLS = {
    "nopipe": "https://raw.githubusercontent.com/ye-kyaw-thu/myPOS/master/corpus-ver-3.0/corpus/mypos-ver.3.0.shuf.nopipe.txt",
    "pipe": "https://raw.githubusercontent.com/ye-kyaw-thu/myPOS/master/corpus-ver-3.0/corpus/mypos-ver.3.0.shuf.txt",
}

ALT_LICENSE = "CC BY-NC-SA 4.0 (NonCommercial) -- https://creativecommons.org/licenses/by-nc-sa/4.0/"
ALT_SOURCE = "https://zenodo.org/records/3463010 (Myanmar ALT, Asian Language Treebank)"
_ALT_URL = "https://zenodo.org/records/3463010/files/my-alt-190530.zip"


@dataclass(frozen=True)
class GoldSentence:
    """One gold-segmented sentence.

    ``words``/``tags`` are already de-piped for the ``pipe`` scheme: each
    entry is one gold token as that scheme defines it (a myPOS compound
    is one entry, tag-less, since a compound's parts may carry different
    POS tags and the merge is about word boundaries, not tagging).
    """

    words: List[str]
    tags: List[Optional[str]]
    raw_line: str


def _download(url: str, dest: Path) -> Path:
    if dest.exists():
        return dest
    logger.info("Downloading %s -> %s", url, dest)
    request = urllib.request.Request(url, headers={"User-Agent": "burmesenlp-bench/1.1"})
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 (fixed https URL)
        data = response.read()
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.write_bytes(data)
    tmp.rename(dest)
    return dest


def _parse_piece(piece: str) -> "tuple[str, Optional[str]]":
    if "/" in piece:
        word, tag = piece.rsplit("/", 1)
        return word, tag
    return piece, None


def _parse_line_nopipe(line: str) -> GoldSentence:
    words: List[str] = []
    tags: List[Optional[str]] = []
    for piece in line.split():
        w, t = _parse_piece(piece)
        if w:
            words.append(w)
            tags.append(t)
    return GoldSentence(words=words, tags=tags, raw_line=line)


def _parse_line_pipe(line: str) -> GoldSentence:
    words: List[str] = []
    tags: List[Optional[str]] = []
    for piece in line.split():
        # a piece may be "word/tag" or a "|"-joined compound run of those
        sub_units = piece.split("|")
        compound_word = ""
        first_tag: Optional[str] = None
        for su in sub_units:
            w, t = _parse_piece(su)
            compound_word += w
            if first_tag is None:
                first_tag = t
        if compound_word:
            words.append(compound_word)
            tags.append(first_tag)
    return GoldSentence(words=words, tags=tags, raw_line=line)


def load_mypos(
    scheme: str = "nopipe",
    *,
    limit: Optional[int] = None,
    cache_dir: Optional[Path] = None,
) -> List[GoldSentence]:
    """Load myPOS v3.0 gold sentences, downloading to the corpus cache
    on first use. Logs the license on every call -- see module docstring.
    """
    if scheme not in _MYPOS_URLS:
        raise ValueError(f"unknown myPOS scheme {scheme!r}; choose from {sorted(_MYPOS_URLS)}")

    logger.warning(
        "myPOS v3.0 is %s. Source: %s. Not vendored; cached locally, "
        "not shipped in the burmesenlp wheel. Do not persist "
        "myPOS-derived artifacts (e.g. n-gram counts) into Apache-2.0 "
        "code -- see burmesenlp.bench module docstring.",
        MYPOS_LICENSE,
        MYPOS_SOURCE,
    )

    root = cache_dir or corpus_cache_dir()
    dest = root / f"mypos-v3.0-{scheme}.txt"
    _download(_MYPOS_URLS[scheme], dest)

    parse = _parse_line_nopipe if scheme == "nopipe" else _parse_line_pipe
    sentences: List[GoldSentence] = []
    with dest.open(encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            sentences.append(parse(line))
            if limit is not None and len(sentences) >= limit:
                break
    return sentences


def _download_and_unzip(url: str, extract_dir: Path, member: str) -> Path:
    dest = extract_dir / member.replace("/", "_")
    if dest.exists():
        return dest
    logger.info("Downloading %s -> %s", url, extract_dir)
    request = urllib.request.Request(url, headers={"User-Agent": "burmesenlp-bench/1.1"})
    with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310 (fixed https URL)
        data = response.read()
    zip_path = extract_dir / "_download.zip.part"
    zip_path.write_bytes(data)
    with zipfile.ZipFile(zip_path) as zf:
        with zf.open(member) as src, dest.open("wb") as out:
            out.write(src.read())
    zip_path.unlink()
    return dest


def _tokenize_sexpr(s: str) -> List[str]:
    tokens: List[str] = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c in "()":
            tokens.append(c)
            i += 1
        elif c.isspace():
            i += 1
        else:
            j = i
            while j < n and s[j] not in "() \t":
                j += 1
            tokens.append(s[i:j])
            i = j
    return tokens


def _parse_sexpr(tokens: List[str], pos: int) -> "tuple[tuple, int]":
    """Recursive-descent parser for one bracketed node starting at
    tokens[pos] == '('. Returns (tree, next_pos).

    tree is either ("leaf", tag, word) -- a node whose only child is a
    bare word atom, structurally a terminal regardless of what its tag
    happens to be named (ALT reuses lowercase tags like "noun" at both
    leaf and phrase level; leaf-ness is structural, not tag-based) -- or
    ("node", tag, [children]) for an internal phrase node.
    """
    assert tokens[pos] == "("
    pos += 1
    tag = tokens[pos]
    pos += 1
    children = []
    while tokens[pos] != ")":
        if tokens[pos] == "(":
            child, pos = _parse_sexpr(tokens, pos)
            children.append(child)
        else:
            children.append(("word", tokens[pos]))
            pos += 1
    pos += 1  # consume ')'
    if len(children) == 1 and children[0][0] == "word":
        return ("leaf", tag, children[0][1]), pos
    return ("node", tag, children), pos


def _extract_leaves(tree: tuple) -> List["tuple[str, str]"]:
    if tree[0] == "leaf":
        return [(tree[1], tree[2])]
    out: List["tuple[str, str]"] = []
    for child in tree[2]:
        out.extend(_extract_leaves(child))
    return out


def _parse_alt_line(line: str) -> Optional[GoldSentence]:
    if "\t" not in line:
        return None
    _sent_id, tree_str = line.split("\t", 1)
    tokens = _tokenize_sexpr(tree_str)
    if not tokens:
        return None
    tree, end = _parse_sexpr(tokens, 0)
    if end != len(tokens):
        raise ValueError(f"trailing tokens after parsing ALT tree: {tokens[end:]!r}")
    leaves = _extract_leaves(tree)
    words = [w for _tag, w in leaves]
    tags: List[Optional[str]] = [tag for tag, _w in leaves]
    return GoldSentence(words=words, tags=tags, raw_line=line)


def load_alt(
    *,
    limit: Optional[int] = None,
    cache_dir: Optional[Path] = None,
) -> List[GoldSentence]:
    """Load the Myanmar ALT (Asian Language Treebank) gold sentences,
    downloading to the corpus cache on first use. Logs the license on
    every call -- see module docstring.

    ALT ships as bracketed constituency parse trees (Penn Treebank
    style), not a flat word/tag sequence like myPOS. Word segmentation
    is the leaf tokens in document order; leaf tags are ALT's own
    Uni-POS scheme (noun/verb/adj/adv/adp/det/conj/part/pron/num/punct,
    lowercase, sometimes hyphen-compounded e.g. "noun-adp") -- a
    different, independent tokenization scheme from both myPOS's and
    burmesenlp's own tagset. Declare "ALT-uni-pos" in any output that
    reports a score against this corpus.
    """
    logger.warning(
        "Myanmar ALT is %s. Source: %s. Not vendored; cached locally, "
        "not shipped in the burmesenlp wheel. Do not persist "
        "ALT-derived artifacts into Apache-2.0 code -- see "
        "burmesenlp.bench module docstring.",
        ALT_LICENSE,
        ALT_SOURCE,
    )

    root = cache_dir or corpus_cache_dir()
    dest = _download_and_unzip(_ALT_URL, root, "my-alt-190530/data")

    sentences: List[GoldSentence] = []
    with dest.open(encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            parsed = _parse_alt_line(line)
            if parsed is None or not parsed.words:
                continue
            sentences.append(parsed)
            if limit is not None and len(sentences) >= limit:
                break
    return sentences


def collapse_stats(sentences: Sequence[GoldSentence]) -> "tuple[int, int, int]":
    """Return (distinct_raw_forms, distinct_canonical_forms, collapsed_count)
    across every gold word in *sentences*, for the load-time collapse log
    required before trusting boundary scores (see requirement 3).
    """
    from ..normalize import canonical_order

    raw_forms = set()
    canon_forms = set()
    for s in sentences:
        for w in s.words:
            raw_forms.add(w)
            canon_forms.add(canonical_order(w))
    return len(raw_forms), len(canon_forms), len(raw_forms) - len(canon_forms)
