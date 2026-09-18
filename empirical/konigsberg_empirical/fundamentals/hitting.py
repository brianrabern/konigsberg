"""Hitting all maximum cliques with an independent set (Rabern 2011).

The property: ∃ an independent set I meeting every *maximum* clique of G. This is
false in general — the smallest counterexample is C₅ (for triangle-free graphs the
maximum cliques are the edges, so the property becomes "independent vertex cover",
which exists iff the graph is bipartite; C₅ is the smallest non-bipartite
triangle-free graph). Rabern gave sufficient conditions for the property to hold;
this module decides it per graph and returns a re-checkable witness.
"""
from __future__ import annotations

import networkx as nx

from ..core import Graph
from .codec import to_nx


def maximum_cliques(g: Graph) -> tuple[int, list[list[int]]]:
    """(ω, list of the maximum cliques as sorted vertex lists)."""
    GX = to_nx(g)
    cliques = list(nx.find_cliques(GX))
    if not cliques:
        return 0, []
    omega = max(len(c) for c in cliques)
    return omega, [sorted(c) for c in cliques if len(c) == omega]


def _independent(GX, verts) -> bool:
    vs = list(verts)
    return not any(
        GX.has_edge(vs[i], vs[j])
        for i in range(len(vs))
        for j in range(i + 1, len(vs))
    )


def independent_hitting_set(g: Graph) -> tuple[bool, list[int] | None]:
    """Decide whether some independent set meets every maximum clique.

    Returns (True, witness independent hitting set) or (False, None) after a
    complete backtracking search (pick one vertex per maximum clique, keeping the
    running choice independent).
    """
    GX = to_nx(g)
    _, Qs = maximum_cliques(g)
    if not Qs:
        return True, []
    chosen: list[int] = []
    chosen_set: set[int] = set()

    def bt(i: int) -> bool:
        if i == len(Qs):
            return True
        if any(v in chosen_set for v in Qs[i]):  # clique i already hit
            return bt(i + 1)
        for v in Qs[i]:
            if any(GX.has_edge(v, u) for u in chosen):
                continue
            chosen.append(v)
            chosen_set.add(v)
            if bt(i + 1):
                return True
            chosen.pop()
            chosen_set.discard(v)
        return False

    if bt(0):
        return True, sorted(chosen_set)
    return False, None


def verify_independent_hitting_set(g: Graph, hitting: list[int]) -> bool:
    """Re-check a witness: it is independent AND meets every maximum clique."""
    GX = to_nx(g)
    iset = set(hitting)
    if not _independent(GX, iset):
        return False
    _, Qs = maximum_cliques(g)
    return all(iset & set(q) for q in Qs)
