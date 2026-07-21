import pytest

from burmesenlp.normalize import looks_like_zawgyi, normalize


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
