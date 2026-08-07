"""Enumeration and random graphs → graph6 strings."""
from __future__ import annotations

import networkx as nx

from ..search.enumerate import all_graphs
from .codec import canonical_graph6, from_nx


def enumerate_graph6(
    n: int,
    *,
    connected: bool = False,
    min_degree: int | None = None,
    regular: int | None = None,
    max_hits: int | None = None,
) -> list[str]:
    constraints: dict = {}
    if connected:
        constraints["connected"] = True
    if min_degree is not None:
        constraints["min_degree"] = min_degree
    hits: list[str] = []
    for g in all_graphs(n, constraints=constraints or None):
        if regular is not None:
            degs = [g.degree(v) for v in range(g.n)]
            if not degs or max(degs) != regular or min(degs) != regular:
                continue
        hits.append(canonical_graph6(g))
        if max_hits is not None and len(hits) >= max_hits:
            break
    return hits


def random_gnp(n: int, p: float, seed: int | None = None) -> str:
    G = nx.gnp_random_graph(n, p, seed=seed)
    # drop self-loops if any (gnp shouldn't have them)
    g = from_nx(G)
    return canonical_graph6(g)
