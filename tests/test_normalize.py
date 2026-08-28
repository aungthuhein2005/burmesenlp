import pytest

from burmesenlp.normalize import canonical_order, looks_like_zawgyi, normalize


def test_strips_zero_width_characters():
    assert normalize("\u1005\u102c\u200b\u1015\u1031") == "\u1005\u102c\u1015\u1031"
    assert normalize("\ufeff\u1019\u103c\u1014\u103a\u1019\u102c") == "\u1019\u103c\u1014\u103a\u1019\u102c"


def test_nfc_composition():
    # U+1025 + U+102E composes to U+1026 (ဦ)
    assert normalize("\u1025\u102e") == "\u1026"


def test_empty_and_type_validation():
    assert normalize("") == ""
    with pytest.raises(TypeError):
        normalize(None)
    with pytest.raises(TypeError):
        normalize(b"bytes")


def test_zawgyi_heuristic():
    # Vowel-e before its consonant is a Zawgyi-typical order.
    assert looks_like_zawgyi("\u1031\u101b")       # ေရ (Zawgyi order)
    assert not looks_like_zawgyi("\u101b\u1031")   # ရေ (Unicode order)
    assert not looks_like_zawgyi("\u1019\u103c\u1031")  # မြေ is valid Unicode
    assert not looks_like_zawgyi("မြန်မာစာပေ")
def test_nfc_does_not_fix_myanmar_mark_order():
    # Medials have Canonical_Combining_Class 0, so NFC leaves distinct
    # key-press orders as distinct strings -- this is exactly the gap
    # canonical_order() closes; normalize() deliberately does not.
    import unicodedata

    a = "\u1000\u103b\u103d"  # ka + medial ya + medial wa
    b = "\u1000\u103d\u103b"  # ka + medial wa + medial ya (same glyphs, swapped keys)
    assert unicodedata.normalize("NFC", a) != unicodedata.normalize("NFC", b)
    assert normalize(a) != normalize(b)
    assert canonical_order(a) == canonical_order(b)


def test_canonical_order_collapses_real_corpus_collisions():
    # Each pair below is a genuine encoding-variant collision found by
    # scanning the myPOS corpus, Burmese Wikipedia, and the bundled
    # lexicon: same intended word, different medial/vowel/asat key order.
    # None of these are documented "Contractions" sequences.
    pairs = [
        # kyun-daw "I/me": medial ya vs medial wa swapped
        ("\u1000\u103b\u103d\u1014\u103a\u1010\u1031\u102c\u103a",
         "\u1000\u103d\u103b\u1014\u103a\u1010\u1031\u102c\u103a"),
        # khe: vowel ai (U+1032) vs dot below (U+1037) swapped
        ("\u1001\u1032\u1037", "\u1001\u1037\u1032"),
        # thoun "count/number": anusvara vs visarga swapped
        ("\u101e\u102f\u1036\u1038", "\u101e\u102f\u1038\u1036"),
        # thoat: upper vowel vs dot below swapped
        ("\u101e\u102d\u102f\u1037", "\u101e\u102d\u1037\u102f"),
        # medial ya vs asat order (asat empirically ranks after medials --
        # matches the more frequent corpus spelling, 1061:76 in myPOS)
        ("\u1001\u103b\u103a", "\u1001\u103a\u103b"),
    ]
    for a, b in pairs:
        assert a != b, "test fixture pair must be genuinely distinct byte sequences"
        assert canonical_order(a) == canonical_order(b)


def test_canonical_order_does_not_touch_common_asat_final_words():
    # Regression guard for a real bug caught during development: an
    # earlier version force-relocated every asat to a single fixed slot,
    # which corrupted extremely common words ending "vowel + asat" (e.g.
    # ta-w, kya-w) into a form the bundled lexicon no longer recognizes.
    for word in (
        "\u1000\u103b\u103d\u1014\u103a\u1010\u1031\u102c\u103a",  # kyun-daw "I/me"
        "\u1000\u103c\u1031\u102c\u103a",  # kyaw
        "\u1010\u1031\u102c\u103a",  # taw
        "\u101c\u103b\u1031\u102c\u103a",  # lyaw
        "\u1001\u103c\u1031\u102c\u103a",  # chaw
    ):
        assert canonical_order(word) == word


def test_canonical_order_kinzi_and_stacked_consonant_untouched():
    # Kinzi <NGA, ASAT, VIRAMA> stays a fixed unit ahead of its consonant,
    # and a stacked consonant stays attached -- canonical_order is a
    # structural parser, not a blind sort.
    kinzi_ka = "\u1004\u103a\u1039\u1000"  # nga+asat+virama (kinzi) + ka
    assert canonical_order(kinzi_ka) == kinzi_ka

    stacked = "\u101e\u1039\u101e"  # sa + virama + sa (conjunct)
    assert canonical_order(stacked) == stacked


def test_canonical_order_no_op_on_non_myanmar_text():
    assert canonical_order("") == ""
    assert canonical_order("hello world 123") == "hello world 123"


def test_canonical_order_bypasses_documented_contraction_sequences():
    # Unicode 16.0.0 core spec, Myanmar, "Contractions": these two exact
    # sequences are the spec's own worked examples, where asat's position
    # is a fixed spelling convention (not an encoding accident) -- they
    # must be passed through unchanged, not rank-sorted.
    yout_kya = (
        "\u101a\u1031\u102c\u1000\u103a\u103b\u102c\u1038"
    )  # man, husband
    kyun_up = (
        "\u1000\u103b\u103d\u1014\u103a\u102f\u1015\u103a"
    )  # I (first person singular)
    assert canonical_order(yout_kya) == yout_kya
    assert canonical_order(kyun_up) == kyun_up

    # Recognized as a prefix inside compounds too.
    prefixed = "\u1021" + kyun_up  # a-kyun-up, formal "I"
    assert canonical_order(prefixed) == prefixed
    suffixed = yout_kya + "\u101c\u1031\u1038"  # yout-kya + "-lay" suffix
    assert canonical_order(suffixed) == suffixed


def test_canonical_order_contraction_variants_no_longer_collapse():
    # Trade-off, made deliberately: bypassing the documented sequence
    # verbatim means its alternate (non-spec) spelling is no longer
    # merged with it by canonical_order -- spec conformance over
    # collision-collapsing for this one rare, explicitly-documented case.
    a = "\u101a\u1031\u102c\u1000\u103a\u103b\u102c\u1038"  # spec spelling
    b = "\u101a\u1031\u102c\u1000\u103b\u102c\u103a\u1038"  # alternate spelling
    assert a != b
    assert canonical_order(a) == a
    assert canonical_order(b) == b
    assert canonical_order(a) != canonical_order(b)


def test_canonical_order_no_false_merges_in_bundled_lexicon():
    # Regression guard: canonical_order must not conflate genuinely
    # distinct words, and must be a near-total no-op over an
    # already-well-formed lexicon. Every collision found must be a real
    # encoding-variant duplicate, not a false merge.
    from collections import defaultdict

    from burmesenlp.lexicon import Lexicon

    lex = Lexicon.default()
    words = list(lex._entries)
    changed = [w for w in words if canonical_order(w) != w]
    # As of the bundled lexicon: only 2 non-contraction duplicate-encoding
    # entries change (dot-below/asat and anusvara/dot-below reordering);
    # the Contractions-pattern entries are now bypassed unchanged.
    assert len(changed) == 2

    groups = defaultdict(list)
    for word in words:
        groups[canonical_order(word)].append(word)
    merged = [v for v in groups.values() if len(v) > 1]
    assert len(merged) == 2
