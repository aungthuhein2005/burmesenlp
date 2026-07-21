"""Tests for Zawgyi <-> Unicode conversion."""

import json

import pytest

from burmesenlp import cli
from burmesenlp.zawgyi import is_zawgyi, to_unicode, uni2zg, zg2uni

UNICODE_SAMPLE = "မြန်မာစာပေ"
# Known Zawgyi rendering of the same phrase (Rabbit uni2zg output).
ZAWGYI_SAMPLE = "ျမန္မာစာေပ"


def test_uni2zg_produces_zawgyi_order():
    zg = uni2zg(UNICODE_SAMPLE)
    assert is_zawgyi(zg)
    assert zg == ZAWGYI_SAMPLE


def test_zg2uni_roundtrip():
    assert zg2uni(uni2zg(UNICODE_SAMPLE)) == UNICODE_SAMPLE
    assert zg2uni(ZAWGYI_SAMPLE) == UNICODE_SAMPLE


def test_is_zawgyi_detects_common_forms():
    assert is_zawgyi(ZAWGYI_SAMPLE)
    assert is_zawgyi("\u1031\u101b")  # ေ before base (Zawgyi order)
    assert not is_zawgyi(UNICODE_SAMPLE)
    assert not is_zawgyi("ရေ")  # Unicode order
    assert not is_zawgyi("")


def test_to_unicode_converts_only_when_needed():
    assert to_unicode(ZAWGYI_SAMPLE) == UNICODE_SAMPLE
    assert to_unicode(UNICODE_SAMPLE) == UNICODE_SAMPLE
    # NFC: U+1025 + U+102E -> U+1026
    assert to_unicode("\u1025\u102e") == "\u1026"
    assert to_unicode("\u1025\u102e", normalize=False) == "\u1025\u102e"


def test_type_validation():
    with pytest.raises(TypeError):
        uni2zg(None)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        zg2uni(123)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        is_zawgyi(b"x")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        to_unicode([])  # type: ignore[arg-type]


def test_cli_zg2uni(capsys):
    rc = cli.main(["--mode", "zg2uni", ZAWGYI_SAMPLE])
    assert rc == 0
    assert capsys.readouterr().out.strip() == UNICODE_SAMPLE


def test_cli_uni2zg(capsys):
    rc = cli.main(["--mode", "uni2zg", UNICODE_SAMPLE])
    assert rc == 0
    assert capsys.readouterr().out.strip() == ZAWGYI_SAMPLE


def test_cli_to_unicode_json(capsys):
    rc = cli.main(["--mode", "to-unicode", "--json", ZAWGYI_SAMPLE])
    assert rc == 0
    assert json.loads(capsys.readouterr().out) == UNICODE_SAMPLE
