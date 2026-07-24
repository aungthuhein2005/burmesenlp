"""Token-sequence trie for O(depth) MWE lookup."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from .models import MWEEntry


class TrieNode:
    __slots__ = ("children", "entries")

    def __init__(self) -> None:
        self.children: Dict[str, TrieNode] = {}
        self.entries: List[MWEEntry] = []


class MWETrie:
    """Trie keyed by successive word tokens (not raw characters)."""

    def __init__(self) -> None:
        self._root = TrieNode()
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def insert(self, entry: MWEEntry) -> None:
        if not entry.tokens:
            return
        node = self._root
        for tok in entry.tokens:
            child = node.children.get(tok)
            if child is None:
                child = TrieNode()
                node.children[tok] = child
            node = child
        # Replace same token-sequence with higher priority; else append
        replaced = False
        for i, existing in enumerate(node.entries):
            if existing.tokens == entry.tokens:
                if entry.priority >= existing.priority:
                    node.entries[i] = entry
                replaced = True
                break
        if not replaced:
            node.entries.append(entry)
            self._size += 1

    def search(self, tokens: Sequence[str], start: int) -> List[MWEEntry]:
        """Return all entries that match a prefix of ``tokens[start:]``."""
        hits: List[MWEEntry] = []
        node: Optional[TrieNode] = self._root
        i = start
        n = len(tokens)
        while node is not None and i < n:
            node = node.children.get(tokens[i])
            if node is None:
                break
            if node.entries:
                hits.extend(node.entries)
            i += 1
        return hits
