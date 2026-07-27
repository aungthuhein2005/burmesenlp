"""Phrase-sequence pattern matching for clause licensing.

V1 uses an explicit enumerated list of phrase templates in YAML
(``NP PP VP``, ``NP VP``, …). That is a deliberate trade-off:
linguist-readable and deterministic, but it does not scale as new
phrase types (ADJP, ADVP, TIME_PHRASE, …) appear.

TODO(V2): replace this matcher with a grammar-based engine without
changing :class:`ClauseParser`'s public API. Candidates:

* productions such as ``Clause ::= NP? PP* VP``
* finite-state / constituency grammar over phrase labels
* parser combinators / declarative rule engine

Keep matching behind :class:`PhrasePatternMatcher` so the swap is local.
"""

from __future__ import annotations

from typing import List, Protocol, Sequence, Tuple


class PhrasePatternMatcher(Protocol):
    """Replaceable phrase-label sequence matcher (V1 explicit list)."""

    def matches(
        self,
        labels: Sequence[str],
        patterns: Sequence[Tuple[str, ...]],
    ) -> bool:
        """Return True if *labels* is licensed by any *patterns* entry."""


class ExplicitListMatcher:
    """V1 matcher: exact / suffix / subsequence match over explicit lists.

    Also accepts a small set of quantified atoms (``(NP|PP)+``) if a linguist
    adds them, but the shipped ``clause_rules.yml`` prefers plain lists.
    """

    def matches(
        self,
        labels: Sequence[str],
        patterns: Sequence[Tuple[str, ...]],
    ) -> bool:
        if not patterns:
            return True
        labs = list(labels)
        for pat in patterns:
            if not pat:
                continue
            if _match_one(labs, pat):
                return True
        return False


_DEFAULT_MATCHER: PhrasePatternMatcher = ExplicitListMatcher()


def default_pattern_matcher() -> PhrasePatternMatcher:
    return _DEFAULT_MATCHER


def _parse_atom(atom: str) -> Tuple[set, str]:
    a = atom.strip()
    quant = ""
    if a and a[-1] in "*+?":
        quant = a[-1]
        a = a[:-1]
    if a.startswith("(") and a.endswith(")"):
        a = a[1:-1]
    alts = {x.strip().upper() for x in a.split("|") if x.strip()}
    return alts, quant


def _atom_has_quant(atom: str) -> bool:
    return atom.endswith(("*", "+", "?"))


def _match_one(labels: List[str], pattern: Sequence[str]) -> bool:
    if _match_atoms(labels, 0, list(pattern), 0):
        return True
    # Optional leading ADJP / NUMP / FIXED_EXPRESSION noise.
    i = 0
    while i < len(labels) and labels[i] in {"ADJP", "NUMP", "FIXED_EXPRESSION"}:
        i += 1
    if i and _match_atoms(labels[i:], 0, list(pattern), 0):
        return True
    if not any(_atom_has_quant(a) for a in pattern):
        flat = tuple(
            a.upper().strip("()") if "|" not in a else a.upper()
            for a in pattern
        )
        # Simple atoms only for suffix / subsequence.
        if all("|" not in a and not _atom_has_quant(a) for a in pattern):
            flat = tuple(a.upper().strip("()") for a in pattern)
            if len(labels) >= len(flat) and tuple(labels[-len(flat) :]) == flat:
                return True
            return _subsequence_match(labels, flat)
    return False


def _match_atoms(
    labels: List[str], li: int, atoms: List[str], ai: int
) -> bool:
    if ai >= len(atoms):
        return li >= len(labels)
    alts, quant = _parse_atom(atoms[ai])
    if not alts:
        return False

    def ok(pos: int) -> bool:
        return pos < len(labels) and labels[pos] in alts

    if quant == "":
        if not ok(li):
            return False
        return _match_atoms(labels, li + 1, atoms, ai + 1)

    if quant == "?":
        if ok(li) and _match_atoms(labels, li + 1, atoms, ai + 1):
            return True
        return _match_atoms(labels, li, atoms, ai + 1)

    if quant == "*":
        pos = li
        while ok(pos):
            pos += 1
        while pos >= li:
            if _match_atoms(labels, pos, atoms, ai + 1):
                return True
            pos -= 1
        return False

    if quant == "+":
        if not ok(li):
            return False
        pos = li + 1
        while ok(pos):
            pos += 1
        while pos > li:
            if _match_atoms(labels, pos, atoms, ai + 1):
                return True
            pos -= 1
        return False

    return False


def _subsequence_match(labels: Sequence[str], pat: Sequence[str]) -> bool:
    n, m = len(labels), len(pat)
    if m > n:
        return False
    for i in range(n - m + 1):
        if tuple(labels[i : i + m]) == tuple(pat):
            return True
    return False
