"""Regression test for the stdin-encoding bug: on Windows, sys.stdin
defaults to the console's legacy code page (cp1252 here), not UTF-8, and
silently mis-decodes Myanmar text instead of raising -- mojibake, no
error. This must be tested via a real subprocess with a real piped
stdin, not by monkeypatching sys.stdin in-process: the bug is about what
the OS/interpreter picks as the *default* codec before any of our code
runs, and an in-process stand-in can't reproduce that default.

The bug survived until someone actually piped real Myanmar text through
and looked at the output (see cli/__init__.py's module docstring). This
test exists so that cannot happen silently a second time.
"""

import os
import subprocess
import sys
from pathlib import Path

_SRC = str(Path(__file__).resolve().parent.parent / "src")

_RUN_CLI = "from burmesenlp.cli import main; raise SystemExit(main(['--mode', 'words']))"


def _clean_env():
    """Environment with every UTF-8-forcing override removed, so the
    interpreter falls back to its real platform default -- exactly the
    condition the original bug reproduced under. A stale burmesenlp is
    pip-installed in this environment (checked: version 1.0.1, unrelated
    to the source tree under test), so PYTHONPATH is set to make sure
    the subprocess imports the code being tested, not that stale copy.
    """
    env = os.environ.copy()
    for var in ("PYTHONIOENCODING", "PYTHONUTF8", "PYTHONLEGACYWINDOWSSTDIO"):
        env.pop(var, None)
    env["PYTHONPATH"] = _SRC
    return env


def test_cli_reads_utf8_from_stdin_without_any_encoding_override():
    text = "မြန်မာစာ"
    proc = subprocess.run(
        [sys.executable, "-c", _RUN_CLI],
        input=text.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_clean_env(),
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr.decode("utf-8", errors="replace")
    assert proc.stdout.decode("utf-8").strip() == text


def test_cli_reads_utf8_from_stdin_for_longer_mixed_text():
    text = "မြန်မာနိုင်ငံ၏ GDP သည် 2024 ခုနှစ်တွင် ၅ ရာခိုင်နှုန်း တိုးတက်ခဲ့သည်။"
    proc = subprocess.run(
        [sys.executable, "-c", _RUN_CLI],
        input=text.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_clean_env(),
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr.decode("utf-8", errors="replace")
    out = proc.stdout.decode("utf-8").strip()
    # word_tokenize() drops inter-word whitespace (verified directly:
    # "".join(word_tokenize(text)) == text.replace(" ", ""), NOT
    # out.replace(" | ", "") == text -- the CLI's " | " joiner isn't the
    # original spacing). Un-join on the CLI's own separator and compare
    # against that verified invariant, so this only fails on genuine
    # mis-decoding, not on a wrong assumption about spacing.
    words = out.split(" | ")
    assert "".join(words) == text.replace(" ", "")
    # The mojibake failure mode replaces every Myanmar byte with garbage
    # Latin-1/cp1252 characters -- guard against that class directly.
    assert "á€" not in out
