"""Load phrase grammar YAML: rules, markers, and exceptions."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, FrozenSet, List, Mapping, Optional, Tuple

from .matcher import (
    CompiledPattern,
    compile_pattern,
    default_aliases,
    normalize_pattern,
)
from .models import (
    ChunkRule,
    ChunkType,
    ClauseKindRules,
    ClauseRules,
    ClauseSettings,
    ClauseType,
    GrammarError,
    PhraseExceptions,
    PhraseMarkers,
    PostpositionRole,
    PostpositionRoles,
)

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "PyYAML is required for burmesenlp.chunking; install with "
        '`pip install "burmesenlp"` or `pip install pyyaml`'
    ) from exc

_GRAMMAR_DIR = Path(__file__).resolve().parent.parent / "corpus" / "grammar"

_TYPE_MAP = {
    "NP": ChunkType.NOUN_PHRASE,
    "NOUN_PHRASE": ChunkType.NOUN_PHRASE,
    "VP": ChunkType.VERB_PHRASE,
    "VERB_PHRASE": ChunkType.VERB_PHRASE,
    "PP": ChunkType.POSTPOSITIONAL_PHRASE,
    "POSTPOSITIONAL_PHRASE": ChunkType.POSTPOSITIONAL_PHRASE,
    "ADJP": ChunkType.ADJECTIVE_PHRASE,
    "ADJECTIVE_PHRASE": ChunkType.ADJECTIVE_PHRASE,
    "NUMP": ChunkType.NUMERAL_PHRASE,
    "NUMERAL_PHRASE": ChunkType.NUMERAL_PHRASE,
    "CLAUSE": ChunkType.CLAUSE,
    "MAIN_CLAUSE": ChunkType.MAIN_CLAUSE,
    "SUBORDINATE_CLAUSE": ChunkType.SUBORDINATE_CLAUSE,
    "RELATIVE_CLAUSE": ChunkType.RELATIVE_CLAUSE,
    "CONDITIONAL_CLAUSE": ChunkType.CONDITIONAL_CLAUSE,
    "GREETING": ChunkType.GREETING,
    "FIXED_EXPRESSION": ChunkType.FIXED_EXPRESSION,
    "FIXED_VERB": ChunkType.FIXED_VERB,
    "INTJ": ChunkType.GREETING,  # map INTJ exceptions to GREETING chunk
}

_PHRASE_KEYS = {
    ChunkType.NOUN_PHRASE: ("NOUN_PHRASE", "NP"),
    ChunkType.VERB_PHRASE: ("VERB_PHRASE", "VP"),
    ChunkType.POSTPOSITIONAL_PHRASE: ("POSTPOSITIONAL_PHRASE", "PP"),
    ChunkType.ADJECTIVE_PHRASE: ("ADJECTIVE_PHRASE", "ADJP"),
    ChunkType.NUMERAL_PHRASE: ("NUMERAL_PHRASE", "NUMP"),
    ChunkType.CLAUSE: ("CLAUSE",),
}


def grammar_dir() -> Path:
    return _GRAMMAR_DIR


def _load_yaml(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise GrammarError(f"cannot read grammar file {path}: {exc}") from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise GrammarError(f"invalid YAML in {path}: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise GrammarError(
            f"{path.name}: root must be a mapping, got {type(data).__name__}"
        )
    return data


def load_aliases() -> Dict[str, FrozenSet[str]]:
    return default_aliases()


def _flatten_marker_groups(raw: object, source: str) -> Dict[str, Tuple[str, ...]]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise GrammarError(f"{source}: marker group must be a mapping")
    out: Dict[str, Tuple[str, ...]] = {}
    for key, vals in raw.items():
        if not isinstance(vals, list) or not all(isinstance(v, str) for v in vals):
            raise GrammarError(f"{source}: markers[{key!r}] must be a list of strings")
        out[str(key)] = tuple(vals)
    return out


_CLAUSE_KIND_MAP = {
    "main": ClauseType.MAIN,
    "conditional": ClauseType.CONDITIONAL,
    "reason": ClauseType.REASON,
    "purpose": ClauseType.PURPOSE,
    "relative": ClauseType.RELATIVE,
    "contrast": ClauseType.CONTRAST,
}


def _parse_phrase_patterns(raw: object, source: str) -> Tuple[Tuple[str, ...], ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise GrammarError(f"{source}: phrase_patterns must be a list")
    out: List[Tuple[str, ...]] = []
    for entry in raw:
        if not isinstance(entry, list) or not all(isinstance(x, str) for x in entry):
            raise GrammarError(
                f"{source}: each phrase_pattern must be a list of strings"
            )
        # Keep quantified atoms like (NP|PP)+ as written (upper-case labels only).
        normed: List[str] = []
        for x in entry:
            s = x.strip()
            if not s:
                continue
            # Upper-case bare labels; leave operator atoms intact.
            if s[0] in "([":
                normed.append(s)
            else:
                normed.append(s.upper())
        out.append(tuple(normed))
    return tuple(out)


def _parse_str_list(raw: object, source: str) -> Tuple[str, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list) or not all(isinstance(v, str) for v in raw):
        raise GrammarError(f"{source} must be a list of strings")
    return tuple(dict.fromkeys(v.strip() for v in raw if v.strip()))


def _parse_clause_settings(raw: object, source: str) -> ClauseSettings:
    if raw is None:
        return ClauseSettings()
    if not isinstance(raw, dict):
        raise GrammarError(f"{source}: settings must be a mapping")
    return ClauseSettings(
        require_final_vp=bool(raw.get("require_final_vp", True)),
        allow_nested_relative=bool(raw.get("allow_nested_relative", True)),
        merge_consecutive_pp=bool(raw.get("merge_consecutive_pp", False)),
        prefer_longest_match=bool(raw.get("prefer_longest_match", True)),
        allow_empty_np=bool(raw.get("allow_empty_np", False)),
    )


def load_clause_rules(path: Optional[Path] = None) -> ClauseRules:
    """Load phrase-pattern + marker clause grammar from ``clause_rules.yml``.

    Supports the V1 template schema::

        settings: …
        patterns: { basic_clause: [...], relative_clause: [...] }
        clauses: { conditional: { inherit, relation, markers, … } }

    Legacy top-level keys (``conditional:``, ``main:``, …) are still accepted.
    """
    p = path or (_GRAMMAR_DIR / "clause_rules.yml")
    data = _load_yaml(p)
    settings = _parse_clause_settings(data.get("settings"), f"{p.name}:settings")

    templates: Dict[str, Tuple[Tuple[str, ...], ...]] = {}
    raw_patterns = data.get("patterns") or {}
    if raw_patterns and not isinstance(raw_patterns, dict):
        raise GrammarError(f"{p.name}: patterns must be a mapping")
    if isinstance(raw_patterns, dict):
        for tname, tlist in raw_patterns.items():
            templates[str(tname)] = _parse_phrase_patterns(
                tlist, f"{p.name}:patterns.{tname}"
            )

    # Prefer nested ``clauses:``; fall back to legacy top-level kind keys.
    raw_clauses = data.get("clauses")
    if raw_clauses is None:
        raw_clauses = {
            name: data[name] for name in _CLAUSE_KIND_MAP if name in data
        }
    if not isinstance(raw_clauses, dict):
        raise GrammarError(f"{p.name}: clauses must be a mapping")

    kinds: Dict[str, ClauseKindRules] = {}
    marker_pairs: List[Tuple[str, str]] = []

    for name, ctype in _CLAUSE_KIND_MAP.items():
        raw = raw_clauses.get(name)
        if raw is None:
            continue
        if not isinstance(raw, dict):
            raise GrammarError(f"{p.name}: {name} must be a mapping")

        inherit = str(raw.get("inherit") or "").strip()
        markers = _parse_str_list(raw.get("markers"), f"{p.name}:{name}.markers")
        end_markers = _parse_str_list(
            raw.get("end_markers"), f"{p.name}:{name}.end_markers"
        )
        # Explicit phrase_patterns override inherit (legacy / overrides).
        if "phrase_patterns" in raw and raw.get("phrase_patterns") is not None:
            patterns = _parse_phrase_patterns(
                raw.get("phrase_patterns"), f"{p.name}:{name}.phrase_patterns"
            )
        elif inherit:
            if inherit not in templates:
                raise GrammarError(
                    f"{p.name}: {name} inherit {inherit!r} not in patterns"
                )
            patterns = templates[inherit]
        else:
            patterns = ()

        relation = str(raw.get("relation") or "").strip()
        precedence = int(raw.get("precedence") or 0)
        nesting = bool(raw.get("nesting", False))

        kinds[name] = ClauseKindRules(
            name=name,
            clause_type=ctype,
            markers=markers,
            phrase_patterns=patterns,
            end_markers=end_markers,
            relation=relation,
            precedence=precedence,
            nesting=nesting,
            inherit=inherit,
        )
        for m in markers:
            marker_pairs.append((m, name))

    # Longest marker first (သော်လည်း before သော်, လျှင်မူ before လျှင်)
    marker_pairs.sort(key=lambda x: len(x[0]), reverse=True)
    return ClauseRules(
        kinds=kinds,
        markers_longest=tuple(marker_pairs),
        settings=settings,
        pattern_templates=templates,
    )


def load_postposition_roles(path: Optional[Path] = None) -> PostpositionRoles:
    """Load PP semantic-role heuristics.

    Prefers ``semantic_roles.yml`` (``POSTP:`` map); falls back to legacy
    ``postposition_roles.yml`` (``postpositions:`` map).
    """
    if path is not None:
        return _load_role_file(Path(path))
    primary = _GRAMMAR_DIR / "semantic_roles.yml"
    legacy = _GRAMMAR_DIR / "postposition_roles.yml"
    if primary.is_file():
        return _load_role_file(primary)
    return _load_role_file(legacy)


def _load_role_file(p: Path) -> PostpositionRoles:
    data = _load_yaml(p)
    # New schema: POSTP: { ကို: { default: OBJECT, … } }
    raw = data.get("POSTP")
    if raw is None:
        raw = data.get("postpositions") or {}
    if not isinstance(raw, dict):
        raise GrammarError(f"{p.name}: POSTP/postpositions must be a mapping")
    by_text: Dict[str, PostpositionRole] = {}
    for text, entry in raw.items():
        if not isinstance(entry, dict):
            raise GrammarError(f"{p.name}: postposition {text!r} must be a mapping")
        default_role = str(
            entry.get("default") or entry.get("default_role") or ""
        ).strip()
        gram = str(entry.get("grammatical_function") or "ADJUNCT").strip()
        possible = entry.get("possible") or entry.get("possible_roles") or []
        if not default_role:
            raise GrammarError(f"{p.name}: {text!r} needs default / default_role")
        if not isinstance(possible, list) or not all(isinstance(x, str) for x in possible):
            raise GrammarError(
                f"{p.name}: {text!r} possible/possible_roles must be a string list"
            )
        by_text[str(text)] = PostpositionRole(
            text=str(text),
            default_role=default_role,
            grammatical_function=gram,
            possible_roles=tuple(possible),
        )
    return PostpositionRoles(by_text=by_text)


def load_markers(path: Optional[Path] = None) -> PhraseMarkers:
    p = path or (_GRAMMAR_DIR / "phrase_markers.yml")
    data = _load_yaml(p)
    raw = data.get("markers") or {}
    if not isinstance(raw, dict):
        raise GrammarError(f"{p.name}: 'markers' must be a mapping")
    return PhraseMarkers(
        noun_phrase_end=_flatten_marker_groups(raw.get("noun_phrase_end"), p.name),
        verb_phrase_end=_flatten_marker_groups(raw.get("verb_phrase_end"), p.name),
        clause_boundary=_flatten_marker_groups(raw.get("clause_boundary"), p.name),
    )


def _parse_exception_items(
    items: object,
    source: str,
    type_key: str,
) -> Tuple[Tuple[str, ChunkType], ...]:
    if items is None:
        return ()
    if not isinstance(items, list):
        raise GrammarError(f"{source}: expected a list")
    out: List[Tuple[str, ChunkType]] = []
    for entry in items:
        if not isinstance(entry, dict):
            raise GrammarError(f"{source}: each exception must be a mapping")
        text = entry.get("text")
        typ = entry.get(type_key) or entry.get("type") or entry.get("chunk")
        if not isinstance(text, str) or not text:
            raise GrammarError(f"{source}: exception needs non-empty 'text'")
        if not isinstance(typ, str) or typ not in _TYPE_MAP:
            raise GrammarError(
                f"{source}: exception type {typ!r} invalid; "
                f"expected one of {sorted(_TYPE_MAP)}"
            )
        out.append((text, _TYPE_MAP[typ]))
    return tuple(out)


def load_exceptions(path: Optional[Path] = None) -> PhraseExceptions:
    p = path or (_GRAMMAR_DIR / "phrase_exceptions.yml")
    data = _load_yaml(p)
    raw = data.get("exceptions") or {}
    if not isinstance(raw, dict):
        raise GrammarError(f"{p.name}: 'exceptions' must be a mapping")
    never = raw.get("never_split") or []
    if not isinstance(never, list) or not all(isinstance(x, str) for x in never):
        raise GrammarError(f"{p.name}: never_split must be a list of strings")
    return PhraseExceptions(
        fixed_expressions=_parse_exception_items(
            raw.get("fixed_expressions"), p.name, "type"
        ),
        never_split=tuple(never),
        special_phrases=_parse_exception_items(
            raw.get("special_phrases"), p.name, "chunk"
        ),
    )


def load_phrase_rules(path: Optional[Path] = None) -> List[ChunkRule]:
    p = path or (_GRAMMAR_DIR / "phrase_rules.yml")
    data = _load_yaml(p)
    phrases = data.get("phrases") or []
    if not isinstance(phrases, list):
        raise GrammarError(f"{p.name}: 'phrases' must be a list")

    rules: List[ChunkRule] = []
    for entry in phrases:
        if not isinstance(entry, dict):
            raise GrammarError(f"{p.name}: each phrase must be a mapping")
        name = entry.get("name")
        rtype = entry.get("type")
        priority = entry.get("priority", 0)
        patterns = entry.get("patterns") or entry.get("pattern")
        features = entry.get("features") or {}

        if not isinstance(name, str) or not name:
            raise GrammarError(f"{p.name}: phrase missing string 'name'")
        if not isinstance(rtype, str) or rtype not in _TYPE_MAP:
            raise GrammarError(
                f"{p.name}: phrase {name!r} has invalid type {rtype!r}; "
                f"expected one of {sorted(_TYPE_MAP)}"
            )
        if not isinstance(priority, int):
            raise GrammarError(f"{p.name}: phrase {name!r} priority must be an int")
        if not isinstance(features, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in features.items()
        ):
            raise GrammarError(f"{p.name}: phrase {name!r} features must be str→str")

        for idx, pat in enumerate(_coerce_patterns(patterns, name, p.name)):
            try:
                dsl = normalize_pattern(pat)
            except GrammarError as exc:
                raise GrammarError(
                    f"{p.name}: phrase {name!r} pattern[{idx}]: {exc}"
                ) from exc
            rules.append(
                ChunkRule(
                    id=f"{name}#{idx}",
                    name=name,
                    type=_TYPE_MAP[rtype],
                    priority=priority,
                    pattern=dsl,
                    source=p.name,
                    features=dict(features),
                )
            )
    rules.sort(key=lambda r: r.priority, reverse=True)
    return rules


def _coerce_patterns(patterns: object, name: str, source: str) -> List[object]:
    """Normalize ``patterns`` / ``pattern`` into a list of pattern entries."""
    if patterns is None:
        raise GrammarError(f"{source}: phrase {name!r} needs patterns")
    if isinstance(patterns, str):
        return [patterns]
    if not isinstance(patterns, list) or not patterns:
        raise GrammarError(f"{source}: phrase {name!r} needs non-empty patterns")
    # [[VERB], [VERB, AUX]] → multiple patterns
    if all(isinstance(p, list) for p in patterns):
        return patterns
    # [VERB, AUX*] → one pattern as atom list
    if all(isinstance(p, str) for p in patterns):
        return [patterns]
    raise GrammarError(
        f"{source}: phrase {name!r} patterns must be a list of lists "
        f"or a flat list of atoms"
    )


def load_all_rules(directory: Optional[Path] = None) -> List[ChunkRule]:
    d = directory or _GRAMMAR_DIR
    return load_phrase_rules(d / "phrase_rules.yml")


def build_phrase_pattern_map(rules: List[ChunkRule]) -> Dict[str, str]:
    """Map phrase names → a core pattern used when expanding refs.

    Prefers the shortest non-POSTP-ending pattern so refs stay NP cores
    (POSTP attachment belongs on PP / explicit NP+POSTP rules).
    """
    by_type: Dict[ChunkType, List[ChunkRule]] = {}
    for rule in rules:
        by_type.setdefault(rule.type, []).append(rule)

    out: Dict[str, str] = {}
    for ctype, group in by_type.items():
        # Prefer patterns without trailing POSTP for core expansion
        core = sorted(
            group,
            key=lambda r: (
                r.pattern.rstrip().endswith("POSTP"),
                len(r.pattern),
                -r.priority,
            ),
        )
        chosen = core[0].pattern
        for key in _PHRASE_KEYS.get(ctype, ()):
            out[key] = chosen
    return out


class CompiledGrammar:
    """Compiled pattern rules + markers + exceptions + clause / role grammars."""

    def __init__(
        self,
        pattern_rules: List[Tuple[ChunkRule, CompiledPattern]],
        markers: PhraseMarkers,
        exceptions: PhraseExceptions,
        aliases: Mapping[str, FrozenSet[str]],
        clause_rules: Optional[ClauseRules] = None,
        postposition_roles: Optional[PostpositionRoles] = None,
    ):
        self.pattern_rules = pattern_rules
        self.markers = markers
        self.exceptions = exceptions
        self.aliases = aliases
        self.clause_rules = clause_rules or ClauseRules({}, ())
        self.postposition_roles = postposition_roles or PostpositionRoles({})
        # Back-compat for older chunker code expecting split_rules
        self.split_rules: List[ChunkRule] = []

    @classmethod
    def from_directory(cls, directory: Optional[Path] = None) -> "CompiledGrammar":
        d = directory or _GRAMMAR_DIR
        rules = load_phrase_rules(d / "phrase_rules.yml")
        markers = load_markers(d / "phrase_markers.yml")
        exceptions = load_exceptions(d / "phrase_exceptions.yml")
        clause_path = d / "clause_rules.yml"
        clause_rules = (
            load_clause_rules(clause_path) if clause_path.is_file() else ClauseRules({}, ())
        )
        roles_path = d / "postposition_roles.yml"
        roles = (
            load_postposition_roles(roles_path)
            if roles_path.is_file()
            else PostpositionRoles({})
        )
        return cls.from_parts(
            rules,
            markers,
            exceptions,
            load_aliases(),
            clause_rules=clause_rules,
            postposition_roles=roles,
        )

    @classmethod
    def from_parts(
        cls,
        rules: List[ChunkRule],
        markers: PhraseMarkers,
        exceptions: PhraseExceptions,
        aliases: Optional[Mapping[str, FrozenSet[str]]] = None,
        clause_rules: Optional[ClauseRules] = None,
        postposition_roles: Optional[PostpositionRoles] = None,
    ) -> "CompiledGrammar":
        aliases = dict(aliases or load_aliases())
        phrase_map = build_phrase_pattern_map(rules)
        pattern_rules: List[Tuple[ChunkRule, CompiledPattern]] = []
        for rule in rules:
            try:
                compiled = compile_pattern(
                    rule.pattern,
                    aliases=aliases,
                    phrase_patterns=phrase_map,
                )
            except GrammarError as exc:
                raise GrammarError(
                    f"{rule.source} rule {rule.id!r}: {exc}"
                ) from exc
            pattern_rules.append((rule, compiled))
        pattern_rules.sort(key=lambda x: x[0].priority, reverse=True)
        return cls(
            pattern_rules,
            markers,
            exceptions,
            aliases,
            clause_rules,
            postposition_roles,
        )

    @classmethod
    def from_rules(
        cls,
        rules: List[ChunkRule],
        aliases: Optional[Mapping[str, FrozenSet[str]]] = None,
    ) -> "CompiledGrammar":
        """Compatibility wrapper used by tests."""
        empty_markers = PhraseMarkers({}, {}, {})
        empty_exc = PhraseExceptions((), (), ())
        return cls.from_parts(rules, empty_markers, empty_exc, aliases)


@lru_cache(maxsize=1)
def default_grammar() -> CompiledGrammar:
    return CompiledGrammar.from_directory()


def reload_default_grammar() -> CompiledGrammar:
    default_grammar.cache_clear()
    return default_grammar()


# Back-compat alias for tests that imported load_rules_from_file
def load_rules_from_file(path: Path) -> List[ChunkRule]:
    """Load phrase rules; supports new ``phrases:`` schema only."""
    return load_phrase_rules(path)
