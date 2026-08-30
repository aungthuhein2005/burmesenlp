"""Zero-config smoke + optional wheel/venv packaging checks."""

from __future__ import annotations

import os
import subprocess
import sys
import venv
from pathlib import Path

import pytest

from burmesenlp import __version__, process

ROOT = Path(__file__).resolve().parents[1]
SMOKE_TEXT = "ကျွန်တော်ကျောင်းသို့သွားသည်။"
EXPECTED_WORDS = ["ကျွန်တော်", "ကျောင်း", "သို့", "သွား", "သည်", "။"]


def test_process_works_without_dictionary_path():
    """Always-on smoke: bundled lexicon, no dictionary_path."""
    doc = process(SMOKE_TEXT, gazetteer=False)
    assert doc["words"] == EXPECTED_WORDS
    assert doc["pos_tags"]
    assert len(doc["pos_tags"]) == len(doc["words"])
    assert doc["sentences"]
    assert __version__ == "1.2.0"


@pytest.mark.packaging
@pytest.mark.skipif(
    os.environ.get("BURMESENLP_PACKAGING_TEST") != "1",
    reason="Set BURMESENLP_PACKAGING_TEST=1 to run wheel/venv install check",
)
def test_fresh_wheel_install_process(tmp_path):
    """Simulate ``pip install burmesenlp`` from a built wheel."""
    dist = tmp_path / "dist"
    dist.mkdir()
    build = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert build.returncode == 0, build.stdout + build.stderr
    wheels = list(dist.glob("burmesenlp-*.whl"))
    assert len(wheels) == 1, f"expected one wheel, got {wheels}"

    venv_dir = tmp_path / "venv"
    venv.create(venv_dir, with_pip=True, clear=True)
    if sys.platform == "win32":
        python = venv_dir / "Scripts" / "python.exe"
        pip = venv_dir / "Scripts" / "pip.exe"
    else:
        python = venv_dir / "bin" / "python"
        pip = venv_dir / "bin" / "pip"

    install = subprocess.run(
        [str(pip), "install", str(wheels[0])],
        capture_output=True,
        text=True,
        check=False,
    )
    assert install.returncode == 0, install.stdout + install.stderr

    probe = r"""
from pathlib import Path
from burmesenlp import process, __version__

assert __version__ == "1.2.0"
doc = process("ကျွန်တော်ကျောင်းသို့သွားသည်။", gazetteer=False)
assert doc["words"] == ["ကျွန်တော်", "ကျောင်း", "သို့", "သွား", "သည်", "။"]
assert doc["pos_tags"]

lex = Path(__import__("burmesenlp").__file__).resolve().parent
assert (lex / "lexicon" / "data" / "default.json").is_file()
assert (lex / "zawgyi" / "zg2uni_rules.json").is_file()
assert (lex / "zawgyi" / "uni2zg_rules.json").is_file()
print("ok")
"""
    run = subprocess.run(
        [str(python), "-c", probe],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert "ok" in run.stdout
