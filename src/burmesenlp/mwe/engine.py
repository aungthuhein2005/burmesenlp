"""BMWEEngine: merge multi-word expressions after word tokenization."""

from __future__ import annotations

import json
import logging
from typing import List, Optional, Sequence, Tuple

from ..lexicon import Lexicon
from .loader import default_idioms_path, load_into_trie
from .matcher import choose
from .models import MWEToken, default_pos_for_category
from .trie import MWETrie
from .validator import AcceptAllValidator, MWEValidator

logger = logging.getLogger(__name__)


def _resolve_entry_pos(entry) -> str:
    if entry.pos:
        return entry.pos
    return default_pos_for_category(entry.category)


class BMWEEngine:
    """Burmese Multi-Word Expression engine (post-tokenization merge)."""

    def __init__(
        self,
        lexicon: Optional[Lexicon] = None,
        validator: Optional[MWEValidator] = None,
        *,
        autoload_idioms: bool = True,
    ):
        self._lexicon = lexicon if lexicon is not None else Lexicon.default()
        self._trie = MWETrie()
        self._validator: MWEValidator = (
            validator if validator is not None else AcceptAllValidator()
        )
        if autoload_idioms:
            path = default_idioms_path()
            if path:
                try:
                    n = self.load(path, category="IDIOM")
                    logger.info("Loaded %d MWE entries from %s", n, path)
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    logger.warning("Could not autoload idioms from %s: %s", path, exc)

    def load(
        self,
        path: str,
        *,
        category: Optional[str] = None,
        priority: int = 0,
        allow_unigrams: bool = False,
        use_cache: bool = True,
        write_cache_on_miss: bool = True,
    ) -> int:
        """Load a JSON/TXT MWE list into the trie. Returns entry count."""
        return load_into_trie(
            self._trie,
            path,
            self._lexicon,
            category=category,
            priority=priority,
            allow_unigrams=allow_unigrams,
            use_cache=use_cache,
            write_cache_on_miss=write_cache_on_miss,
        )

    @property
    def size(self) -> int:
        return len(self._trie)

    def process(self, tokens: Sequence[str]) -> List[str]:
        """Return merged token strings for downstream POS/chunking."""
        merged, _ = self.process_detailed(tokens)
        return merged

    def process_detailed(
        self,
        tokens: Sequence[str],
    ) -> Tuple[List[str], List[MWEToken]]:
        """Greedy left-to-right MWE merge; return strings + span metadata."""
        tokens = list(tokens)
        if not tokens:
            return [], []

        out: List[str] = []
        spans: List[MWEToken] = []
        i = 0
        n = len(tokens)
        while i < n:
            candidates = self._trie.search(tokens, i)
            if not candidates:
                out.append(tokens[i])
                i += 1
                continue
            best = choose(candidates)
            if self._validator.validate(best, tokens, i):
                end = i + len(best.tokens) - 1
                merged_text = "".join(best.tokens)
                merged_index = len(out)
                out.append(merged_text)
                spans.append(
                    MWEToken(
                        text=merged_text,
                        tokens=best.tokens,
                        category=best.category,
                        start=i,
                        end=end,
                        priority=best.priority,
                        pos=_resolve_entry_pos(best),
                        index=merged_index,
                    )
                )
                i = end + 1
            else:
                out.append(tokens[i])
                i += 1
        return out, spans
