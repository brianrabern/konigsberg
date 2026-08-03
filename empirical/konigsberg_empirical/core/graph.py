"""Shared graph representation.

Deliberately tiny and dependency-free at the core so every tier agrees on one
canonical object. networkx is available for convenience elsewhere, but the
canonical form lives here so bridge encoding and differential tests have a
single source of truth.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Graph:
    """Simple undirected graph on vertices 0..n-1. Edges as sorted frozenset pairs."""

    n: int
    edges: frozenset[tuple[int, int]]

    @staticmethod
    def of(n: int, edges) -> "Graph":
        norm = frozenset(tuple(sorted((int(u), int(v)))) for u, v in edges)
        for u, v in norm:
            if not (0 <= u < n and 0 <= v < n) or u == v:
                raise ValueError(f"bad edge ({u},{v}) for n={n}")
        return Graph(n, norm)

    def neighbors(self, v: int) -> set[int]:
        return {b for a, b in self.edges if a == v} | {a for a, b in self.edges if b == v}

    def degree(self, v: int) -> int:
        return len(self.neighbors(v))

    @property
    def max_degree(self) -> int:
        return max((self.degree(v) for v in range(self.n)), default=0)

    def canonical(self) -> "Graph":
        """Canonical form under vertex relabeling. TODO: nauty-backed canon.

        Until wired to nauty, this returns self; differential tests must not rely
        on canonicalization yet."""
        return self
