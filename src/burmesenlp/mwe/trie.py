"""Token-sequence trie for O(depth) MWE lookup (wraps shared TokenTrie)."""

from __future__ import annotations

from typing import List, Sequence

from ..structures.token_trie import TokenTrie, TrieNode
from .models import MWEEntry


class MWETrie:
    """Trie keyed by successive word tokens (not raw characters)."""

    def __init__(self) -> None:
        self._trie: TokenTrie[MWEEntry] = TokenTrie()

    def __len__(self) -> int:
        return len(self._trie)

    def insert(self, entry: MWEEntry) -> None:
        if not entry.tokens:
            return
        node = self._trie._root  # noqa: SLF001 — thin wrapper over shared trie
        for tok in entry.tokens:
            child = node.children.get(tok)
            if child is None:
                child = TrieNode()
                node.children[tok] = child
            node = child
        replaced = False
        for i, existing in enumerate(node.payloads):
            if existing.tokens == entry.tokens:
                if entry.priority >= existing.priority:
                    node.payloads[i] = entry
                replaced = True
                break
        if not replaced:
            node.payloads.append(entry)
            self._trie._size += 1  # noqa: SLF001

    def search(self, tokens: Sequence[str], start: int = 0) -> List[MWEEntry]:
        """Return all entries that match a prefix of ``tokens[start:]``."""
        return self._trie.search(tokens, start)
