"""Hierarchical phrase-based clause parser tests (V1)."""

from __future__ import annotations

import pytest

from burmesenlp import BurmeseNLP, process
from burmesenlp.chunking import (
    ClauseParser,
    ClauseType,
    ChunkType,
    chunk_from_tokens,
    load_clause_rules,
    load_postposition_roles,
    reload_default_grammar,
)
from burmesenlp.chunking.models import ROLE_HEAD_NOUN, ROLE_RELATIVE_MODIFIER


@pytest.fixture(autouse=True)
def _reload_grammar():
    reload_default_grammar()


def _parse(words, tags):
    return ClauseParser().parse_window(chunk_from_tokens(words, tags), words=words)


# ---------------------------------------------------------------------------
# YAML schema
# ---------------------------------------------------------------------------


def test_clause_rules_templates_and_metadata():
    rules = load_clause_rules()
    assert "basic_clause" in rules.pattern_templates
    assert "relative_clause" in rules.pattern_templates
    cond = rules.kind("conditional")
    assert cond is not None
    assert cond.inherit == "basic_clause"
    assert cond.relation == "condition"
    assert cond.precedence == 20
    assert not cond.nesting
    assert cond.phrase_patterns  # inherited
    rel = rules.kind("relative")
    assert rel is not None
    assert rel.nesting is True
    assert rel.relation == "modifier"
    assert any(len(p) >= 3 for p in rel.phrase_patterns)
    assert rules.settings.require_final_vp is True
    assert rules.settings.prefer_longest_match is True


def test_semantic_roles_yml_loads():
    roles = load_postposition_roles()
    ko = roles.get("ကို")
    assert ko is not None
    assert ko.default_role == "OBJECT"


# ---------------------------------------------------------------------------
# Clause types
# ---------------------------------------------------------------------------


def test_main_clause():
    tree = _parse(
        ["ကျွန်တော်", "စာ", "ဖတ်", "နေ", "သည်", "။"],
        ["PRON", "NOUN", "VERB", "AUX", "SFP", "PUNCT"],
    )
    assert len(tree.clauses) == 1
    c = tree.clauses[0]
    assert c.type == ClauseType.MAIN
    assert c.relation == "matrix"
    assert c.phrases
    assert c.chunks is c.phrases
    assert any(p.type == ChunkType.VERB_PHRASE for p in c.chunks)


def test_main_requires_end_marker_inside_vp():
    from burmesenlp.chunking import is_valid_main_clause
    from burmesenlp.chunking.models import Phrase

    # Bare VP without sentence-final marker → not MAIN
    bare = _parse(["သွား"], ["VERB"])
    assert not any(c.type == ClauseType.MAIN for c in bare.clauses)

    # VP + သည် inside the VP → MAIN
    ok = _parse(["သွား", "သည်"], ["VERB", "SFP"])
    assert any(c.type == ClauseType.MAIN for c in ok.clauses)

    # NP + သည် (subject marker / no VP) → not MAIN
    no_vp = _parse(["သူ", "သည်"], ["PRON", "POSTP"])
    assert not any(c.type == ClauseType.MAIN for c in no_vp.clauses)

    # Direct validator: marker alone never licenses MAIN
    fake_np = Phrase(
        type=ChunkType.NOUN_PHRASE,
        text="သည်",
        tokens=["သည်"],
        pos_tags=["PART"],
        start=0,
        end=0,
    )
    assert not is_valid_main_clause(
        [fake_np],
        end_markers=("သည်", "တယ်"),
        phrase_patterns=(("NP", "VP"), ("VP",)),
    )


def test_greeting_is_main():
    tree = _parse(["မင်္ဂလာ", "ပါ"], ["NOUN", "PART"])
    # May be GREETING chunk → MAIN
    assert tree.clauses
    assert tree.clauses[0].type == ClauseType.MAIN


def test_conditional_clause():
    tree = _parse(
        ["မိုး", "ရွာ", "လျှင်", "အိမ်", "မှာ", "နေ", "မည်", "။"],
        ["NOUN", "VERB", "PART", "NOUN", "POSTP", "VERB", "SFP", "PUNCT"],
    )
    types = [c.type for c in tree.clauses]
    assert ClauseType.CONDITIONAL in types
    assert ClauseType.MAIN in types
    cond = next(c for c in tree.clauses if c.type == ClauseType.CONDITIONAL)
    assert cond.marker == "လျှင်"
    assert cond.relation == "condition"
    assert any(p.type == ChunkType.VERB_PHRASE for p in cond.chunks)


def test_reason_clause():
    tree = _parse(
        ["မိုး", "ရွာ", "သောကြောင့်", "မ", "သွား", "ဘူး", "။"],
        ["NOUN", "VERB", "PART", "PART", "VERB", "PART", "PUNCT"],
    )
    assert any(c.type == ClauseType.REASON for c in tree.clauses)
    reason = next(c for c in tree.clauses if c.type == ClauseType.REASON)
    assert reason.relation == "cause"
    assert "ကြောင့်" in reason.marker


def test_contrast_clause():
    tree = _parse(
        ["သူ", "သွား", "ပြီ", "ပေမဲ့", "သူ", "မ", "လာ", "ဘူး", "။"],
        ["PRON", "VERB", "SFP", "CONJ", "PRON", "PART", "VERB", "PART", "PUNCT"],
    )
    # Contrast marker may sit after VP; expect CONTRAST and/or MAIN
    types = {c.type for c in tree.clauses}
    assert ClauseType.MAIN in types or ClauseType.CONTRAST in types
    # If contrast fires, relation is set
    for c in tree.clauses:
        if c.type == ClauseType.CONTRAST:
            assert c.relation == "contrast"
            assert c.marker


def test_purpose_clause_vs_purpose_vp():
    tree_c = _parse(["စာ", "ဖတ်", "ရန်"], ["NOUN", "VERB", "PART"])
    assert any(c.type == ClauseType.PURPOSE for c in tree_c.clauses)
    purpose = next(c for c in tree_c.clauses if c.type == ClauseType.PURPOSE)
    assert purpose.relation == "purpose"
    assert purpose.marker == "ရန်"

    tree_v = _parse(["ဖတ်", "ရန်"], ["VERB", "PART"])
    assert not any(c.type == ClauseType.PURPOSE for c in tree_v.clauses)
    assert any(p.role == "PurposeVP" for p in tree_v.phrases)


def test_relative_nests_inside_np_not_top_level():
    tree = _parse(["လိုအပ်", "သော", "စာအုပ်"], ["VERB", "PART", "NOUN"])
    assert all(c.type != ClauseType.RELATIVE for c in tree.clauses)
    nested = [p for p in tree.phrases if p.children]
    assert nested
    roles = {ch.role for ch in nested[0].children}
    assert ROLE_RELATIVE_MODIFIER in roles
    assert ROLE_HEAD_NOUN in roles


def test_relative_pp_vp_np_pattern():
    """ကျောင်း မှာ သင် တဲ့ ဆရာ → nested NP (PP+VP modifier)."""
    words = ["ကျောင်း", "မှာ", "သင်", "တဲ့", "ဆရာ"]
    tags = ["NOUN", "POSTP", "VERB", "PART", "NOUN"]
    tree = _parse(words, tags)
    assert all(c.type != ClauseType.RELATIVE for c in tree.clauses)
    nested = [p for p in tree.phrases if p.features.get("relative") == "true"]
    assert nested, [p.to_dict() for p in tree.phrases]
    assert nested[0].type == ChunkType.NOUN_PHRASE
    assert any(ch.role == ROLE_RELATIVE_MODIFIER for ch in nested[0].children)
    assert any(ch.role == ROLE_HEAD_NOUN for ch in nested[0].children)


def test_multiple_clauses_conditional_then_main():
    tree = _parse(
        ["မိုး", "ရွာ", "လျှင်", "အိမ်", "မှာ", "နေ", "မည်"],
        ["NOUN", "VERB", "PART", "NOUN", "POSTP", "VERB", "SFP"],
    )
    assert len(tree.clauses) >= 2
    assert tree.clauses[0].type == ClauseType.CONDITIONAL
    assert tree.clauses[-1].type == ClauseType.MAIN


def test_invalid_marker_alone_is_not_a_clause():
    """A lone particle must never become a clause."""
    tree = _parse(["လျှင်"], ["PART"])
    assert tree.clauses == () or not any(
        c.type == ClauseType.CONDITIONAL for c in tree.clauses
    )


def test_empty_sentence():
    tree = ClauseParser().parse_window([], words=[])
    assert tree.clauses == ()
    assert tree.phrases == ()


def test_complex_np_pp_vp_with_conditional():
    words = ["သူ", "ကျောင်း", "ကို", "သွား", "လျှင်", "စာ", "ဖတ်", "မည်"]
    tags = ["PRON", "NOUN", "POSTP", "VERB", "PART", "NOUN", "VERB", "SFP"]
    tree = _parse(words, tags)
    assert any(c.type == ClauseType.CONDITIONAL for c in tree.clauses)
    cond = next(c for c in tree.clauses if c.type == ClauseType.CONDITIONAL)
    # Conditional span retains phrase hierarchy (NP/PP/VP), not flattened words.
    labels = {p.type for p in cond.chunks}
    assert ChunkType.VERB_PHRASE in labels
    assert len(cond.chunks) >= 2


def test_pipeline_document_keeps_hierarchy():
    doc = process("မိုးရွာလျှင်အိမ်မှာနေမည်။", gazetteer=False)
    assert doc.sentence_trees
    assert doc.clauses
    for c in doc.clauses:
        assert c.phrases
        assert c.chunks is c.phrases
        d = c.to_dict()
        assert "chunks" in d and "phrases" in d
        assert "relation" in d


def test_complex_np_pp_vp_licenses_main():
    """Explicit V1 list includes NP PP PP VP for multi-PP sentences."""
    words = ["သူ", "ရန်ကုန်", "ကို", "မနေ့က", "မှာ", "သွား", "သည်"]
    tags = ["PRON", "NOUN", "POSTP", "NOUN", "POSTP", "VERB", "SFP"]
    tree = _parse(words, tags)
    assert any(c.type == ClauseType.MAIN for c in tree.clauses)
    main = next(c for c in tree.clauses if c.type == ClauseType.MAIN)
    assert len(main.chunks) >= 3
