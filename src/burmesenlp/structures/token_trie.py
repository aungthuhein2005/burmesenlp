"""Generic token-sequence trie shared by BMWE and gazetteers."""

from __future__ import annotations

from typing import Callable, Dict, Generic, List, Optional, Sequence, TypeVar

T = TypeVar("T")


class TrieNode(Generic[T]):
    __slots__ = ("children", "payloads")

    def __init__(self) -> None:
        self.children: Dict[str, TrieNode[T]] = {}
        self.payloads: List[T] = []


class TokenTrie(Generic[T]):
    """Trie keyed by successive word tokens (not raw characters)."""

    def __init__(self) -> None:
        self._root: TrieNode[T] = TrieNode()
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def insert(
        self,
        tokens: Sequence[str],
        payload: T,
        *,
        replace_same: Optional[Callable[[T, T], bool]] = None,
    ) -> None:
        """Insert *payload* at the node reached by *tokens*.

        If *replace_same* is provided and returns True for an existing
        payload at the terminal, that slot is replaced; otherwise the new
        payload is appended.
        """
        if not tokens:
            return
        node: TrieNode[T] = self._root
        for tok in tokens:
            child = node.children.get(tok)
            if child is None:
                child = TrieNode()
                node.children[tok] = child
            node = child

        if replace_same is not None:
            for i, existing in enumerate(node.payloads):
                if replace_same(existing, payload):
                    node.payloads[i] = payload
                    return

        node.payloads.append(payload)
        self._size += 1

    def search(self, tokens: Sequence[str], start: int = 0) -> List[T]:
        """Return all payloads on prefixes of ``tokens[start:]``."""
        hits: List[T] = []
        node: Optional[TrieNode[T]] = self._root
        i = start
        n = len(tokens)
        while node is not None and i < n:
            node = node.children.get(tokens[i])
            if node is None:
                break
            if node.payloads:
                hits.extend(node.payloads)
            i += 1
        return hits
