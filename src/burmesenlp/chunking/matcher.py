"""Compile and execute chunking pattern DSL over POS (+ optional word literals).

Pattern grammar (whitespace-separated atoms)::

    ADV? PART? VERB AUX* SFP?
    (ADJ|NUM)? (NOUN|PRON|PROPN)+ POSTP
    VERB+ (word=လို့|word=ပြီး|CONJ)

Operators: ``?`` optional, ``*`` zero-or-more, ``+`` one-or-more,
``(A|B)`` alternatives.  Named phrase refs expand at compile time.
``word=…`` matches the surface token instead of a POS tag.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Mapping, Optional, Sequence, Set, Tuple

from ..lexicon import POS_TAGS
from .models import ChunkType, GrammarError

_PHRASE_REF_NAMES = frozenset(
    {
        "NOUN_PHRASE",
        "NP",
        "VERB_PHRASE",
        "VP",
        "POSTPOSITIONAL_PHRASE",
        "PP",
        "ADJECTIVE_PHRASE",
        "ADJP",
        "NUMERAL_PHRASE",
        "NUMP",
        "CLAUSE",
    }
)

_ATOM_RE = re.compile(
    r"""
    \( (?P<group>[^)]+) \) (?P<gquant>[?*+]?)
  | (?P<word>word=\S+?) (?P<wquant>[?*+]?) (?=\s|$|\))
  | (?P<name>[A-Za-z_][A-Za-z0-9_]*) (?P<nquant>[?*+]?)
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class _Atom:
    tags: FrozenSet[str]
    words: FrozenSet[str]
    quant: str  # "", "?", "*", "+"

    def matches(self, word: str, tag: str) -> bool:
        if self.words and word in self.words:
            return True
        if self.tags and tag in self.tags:
            return True
        return False


@dataclass
class CompiledPattern:
    atoms: List[_Atom]
    source: str

    def match_at(
        self,
        words: Sequence[str],
        tags: Sequence[str],
        start: int,
    ) -> Optional[int]:
        """Return exclusive end index if pattern matches at *start*, else None."""
        return self._match(words, tags, start, 0)

    def _match(
        self,
        words: Sequence[str],
        tags: Sequence[str],
        i: int,
        atom_idx: int,
    ) -> Optional[int]:
        if atom_idx >= len(self.atoms):
            return i
        atom = self.atoms[atom_idx]
        n = len(words)
        quant = atom.quant or ""

        def ok(pos: int) -> bool:
            return pos < n and atom.matches(words[pos], tags[pos])

        if quant == "":
            if not ok(i):
                return None
            return self._match(words, tags, i + 1, atom_idx + 1)

        if quant == "?":
            if ok(i):
                taken = self._match(words, tags, i + 1, atom_idx + 1)
                if taken is not None:
                    return taken
            return self._match(words, tags, i, atom_idx + 1)

        if quant == "*":
            pos = i
            while ok(pos):
                pos += 1
            while pos >= i:
                got = self._match(words, tags, pos, atom_idx + 1)
                if got is not None:
                    return got
                pos -= 1
            return None

        if quant == "+":
            if not ok(i):
                return None
            pos = i + 1
            while ok(pos):
                pos += 1
            while pos > i:
                got = self._match(words, tags, pos, atom_idx + 1)
                if got is not None:
                    return got
                pos -= 1
            return None

        raise GrammarError(f"unknown quantifier {quant!r} in {self.source!r}")


def _split_alts(text: str) -> List[str]:
    return [p.strip() for p in text.split("|") if p.strip()]


def tokenize_pattern(pattern: str) -> List[Tuple[str, str]]:
    pattern = pattern.strip()
    if not pattern:
        raise GrammarError("empty pattern")
    atoms: List[Tuple[str, str]] = []
    pos = 0
    while pos < len(pattern):
        while pos < len(pattern) and pattern[pos].isspace():
            pos += 1
        if pos >= len(pattern):
            break
        m = _ATOM_RE.match(pattern, pos)
        if not m:
            raise GrammarError(
                f"invalid pattern syntax near {pattern[pos : pos + 20]!r} "
                f"in {pattern!r}"
            )
        if m.group("group") is not None:
            atoms.append((m.group("group").strip(), m.group("gquant") or ""))
        elif m.group("word") is not None:
            atoms.append((m.group("word"), m.group("wquant") or ""))
        else:
            atoms.append((m.group("name"), m.group("nquant") or ""))
        pos = m.end()
    if not atoms:
        raise GrammarError(f"no atoms parsed from pattern {pattern!r}")
    return atoms


def _resolve_symbol(
    name: str,
    aliases: Mapping[str, FrozenSet[str]],
) -> Tuple[FrozenSet[str], FrozenSet[str]]:
    if name.startswith("word="):
        return frozenset(), frozenset({name[5:]})
    if name in aliases:
        return aliases[name], frozenset()
    if name in POS_TAGS:
        return frozenset({name}), frozenset()
    raise GrammarError(
        f"unknown pattern symbol {name!r}; "
        f"expected a POS tag, alias, or word=…"
    )


def _atom_from_body(
    body: str,
    quant: str,
    aliases: Mapping[str, FrozenSet[str]],
) -> _Atom:
    tags: Set[str] = set()
    words: Set[str] = set()
    for alt in _split_alts(body):
        t, w = _resolve_symbol(alt, aliases)
        tags |= set(t)
        words |= set(w)
    if not tags and not words:
        raise GrammarError(f"empty alternatives in {body!r}")
    return _Atom(tags=frozenset(tags), words=frozenset(words), quant=quant)


def compile_pattern(
    pattern: str,
    *,
    aliases: Optional[Mapping[str, FrozenSet[str]]] = None,
    phrase_patterns: Optional[Mapping[str, str]] = None,
    _stack: Optional[Tuple[str, ...]] = None,
) -> CompiledPattern:
    """Compile a DSL pattern, expanding phrase references recursively."""
    aliases_map: Dict[str, FrozenSet[str]] = dict(aliases or default_aliases())
    if "PROPN" not in aliases_map:
        aliases_map["PROPN"] = frozenset({"NOUN"})
    phrases = dict(phrase_patterns or {})
    stack = _stack or ()

    atoms: List[_Atom] = []
    for body, quant in tokenize_pattern(pattern):
        # Single-name phrase reference
        if body in phrases or body in _PHRASE_REF_NAMES:
            key = body
            if key not in phrases:
                # Try canonical names
                for cand in (key,):
                    if cand in phrases:
                        key = cand
                        break
                else:
                    raise GrammarError(
                        f"phrase reference {body!r} has no defining pattern"
                    )
            if quant:
                raise GrammarError(
                    f"quantifier on phrase reference {body}{quant} is not supported"
                )
            if key in stack:
                raise GrammarError(f"cyclic phrase reference involving {key!r}")
            inner = compile_pattern(
                phrases[key],
                aliases=aliases_map,
                phrase_patterns=phrases,
                _stack=stack + (key,),
            )
            atoms.extend(inner.atoms)
            continue

        # Alternatives must not contain unresolved phrase refs
        for alt in _split_alts(body):
            if alt in phrases or alt in _PHRASE_REF_NAMES:
                raise GrammarError(
                    f"phrase reference {alt!r} inside alternatives is not supported"
                )

        atoms.append(_atom_from_body(body, quant, aliases_map))

    return CompiledPattern(atoms=atoms, source=pattern)


def default_aliases() -> Dict[str, FrozenSet[str]]:
    return {"PROPN": frozenset({"NOUN"})}


def pattern_list_to_dsl(atoms: Sequence[object]) -> str:
    """Convert a YAML list pattern ``[VERB, AUX*, SFP?]`` to a DSL string."""
    if not isinstance(atoms, (list, tuple)) or not atoms:
        raise GrammarError("pattern list must be a non-empty sequence")
    parts: List[str] = []
    for atom in atoms:
        if not isinstance(atom, str) or not atom.strip():
            raise GrammarError(f"pattern atom must be a non-empty string, got {atom!r}")
        parts.append(atom.strip())
    return " ".join(parts)


def normalize_pattern(pattern: object) -> str:
    """Accept a DSL string or YAML list of atoms and return a DSL string."""
    if isinstance(pattern, str):
        if not pattern.strip():
            raise GrammarError("empty pattern string")
        return pattern.strip()
    if isinstance(pattern, list):
        return pattern_list_to_dsl(pattern)
    raise GrammarError(f"pattern must be a string or list, got {type(pattern).__name__}")


def chunk_type_name(chunk_type: ChunkType) -> str:
    return {
        ChunkType.NOUN_PHRASE: "NOUN_PHRASE",
        ChunkType.VERB_PHRASE: "VERB_PHRASE",
        ChunkType.POSTPOSITIONAL_PHRASE: "POSTPOSITIONAL_PHRASE",
        ChunkType.ADJECTIVE_PHRASE: "ADJECTIVE_PHRASE",
        ChunkType.NUMERAL_PHRASE: "NUMERAL_PHRASE",
        ChunkType.CLAUSE: "CLAUSE",
        ChunkType.MAIN_CLAUSE: "MAIN_CLAUSE",
        ChunkType.SUBORDINATE_CLAUSE: "SUBORDINATE_CLAUSE",
        ChunkType.RELATIVE_CLAUSE: "RELATIVE_CLAUSE",
        ChunkType.CONDITIONAL_CLAUSE: "CONDITIONAL_CLAUSE",
        ChunkType.GREETING: "GREETING",
        ChunkType.FIXED_EXPRESSION: "FIXED_EXPRESSION",
        ChunkType.FIXED_VERB: "FIXED_VERB",
    }[chunk_type]
