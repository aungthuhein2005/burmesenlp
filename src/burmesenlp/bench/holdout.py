"""ALT held-out enforcement.

Decision: iterate against myPOS during development, keep ALT entirely
clean, score it only for a final/reportable measurement. myPOS is
already known-contaminated (its vocabulary is the bundled lexicon's
source, per the canonical_order/bench work), so iterating against it
costs nothing additional; ALT is the one genuinely independent
measurement this project has, and repeated scoring during a tuning loop
("add names -> score ALT -> repeat") is exactly the myPOS contamination
story again, just arriving more slowly.

Enforced two ways, permanently (not just for one project): running
`--corpus alt` requires the explicit `--final` flag -- there is no
accidental or default way to spend the held-out measurement -- and every
`--final` run is appended to a persistent, unremovable-by-this-tool log
in the corpus cache dir, so repeat use is visible in any report rather
than silently possible.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import List, Optional

from .cache import corpus_cache_dir

_LOG_NAME = "alt_holdout_log.jsonl"


def _log_path(cache_dir: Optional[Path] = None) -> Path:
    return (cache_dir or corpus_cache_dir()) / _LOG_NAME


def read_log(cache_dir: Optional[Path] = None) -> List[dict]:
    path = _log_path(cache_dir)
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries


def record_run(reason: Optional[str], cache_dir: Optional[Path] = None) -> List[dict]:
    """Append one entry to the ALT holdout log. Returns the full log
    (including this entry) so the caller can warn on repeat use."""
    path = _log_path(cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {"unix_time": time.time(), "reason": reason or "(no reason given)"}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return read_log(cache_dir)
