"""Borodin-Kostochka attack helpers — bad-K2 / choice-criticality search.

Ported from Brian's bk2.py and rebuilt on the CEGAR engine already in this
package (choosability.find_bad_list). This is the domain-specific layer aimed at
the north star: hunting for k-choice-critical graphs carrying a "bad K2" — the
structure a human BK attack cares about.

Composition, not new solving: the choosability decisions come from
choosability.find_bad_list (SAT/CEGAR, returns a re-checkable certificate). This
module adds the BK-specific predicates and the search that strings them together.

Honesty (inherited from find_bad_list): a found bad list is a CERTAIN,
independently re-checkable witness of "not k-choosable". A None result is a
complete decision only at the default palette (k*n); a smaller palette is a
faster, weaker bound, and any "critical" verdict resting on it inherits that
caveat.
"""
from __future__ import annotations

from collections.abc import Iterable, Iterator
from itertools import combinations

from ..core import Graph
from .choosability import find_bad_list
from .list_checks import is_k_colorable


def without_edge(graph: Graph, edge: tuple[int, int]) -> Graph:
    """G with one edge removed (same vertex set)."""
    u, v = edge
    drop = (min(u, v), max(u, v))
    return Graph(graph.n, frozenset(e for e in graph.edges if e != drop))


def bad_k2_edges(graph: Graph) -> list[tuple[int, int]]:
    """Edges uv with deg(u)=deg(v)=4 whose every *other* neighbour has degree 3.

    The "bad K2" shape from the BK setting (max degree 4, the two endpoints the
    only degree-4 vertices in their combined neighbourhood)."""
    deg = [graph.degree(v) for v in range(graph.n)]
    nbrs = [graph.neighbors(v) for v in range(graph.n)]
    out: list[tuple[int, int]] = []
    for u, v in graph.edges:  # edges are stored as sorted (u<v) tuples
        if deg[u] == deg[v] == 4 and all(
            deg[w] == 3 for w in (nbrs[u] | nbrs[v]) - {u, v}
        ):
            out.append((u, v))
    return out


def has_k4(graph: Graph) -> bool:
    """True iff G contains a K4 (four mutually adjacent vertices)."""
    nbrs = [graph.neighbors(v) for v in range(graph.n)]
    for a, b, c, d in combinations(range(graph.n), 4):
        if (
            b in nbrs[a] and c in nbrs[a] and d in nbrs[a]
            and c in nbrs[b] and d in nbrs[b]
            and d in nbrs[c]
        ):
            return True
    return False


def is_choice_critical(
    graph: Graph, k: int = 3, *, palette: int | None = None
) -> bool:
    """True iff G is edge-choice-critical for k: G is NOT k-choosable, yet every
    single-edge deletion G-e IS k-choosable.

    Both directions rest on find_bad_list, so a True verdict at the default
    palette (k*n) is a complete decision; at a smaller palette it inherits the
    palette caveat.
    """
    if find_bad_list(graph, k, palette=palette) is None:
        return False  # G is k-choosable -> not critical
    return all(
        find_bad_list(without_edge(graph, e), k, palette=palette) is None
        for e in sorted(graph.edges)
    )


def find_bad_k2_critical(
    graphs: Iterable[Graph], k: int = 3, *, palette: int | None = None
) -> Iterator[dict]:
    """Yield k-choice-critical graphs carrying a bad-K2 edge, over `graphs`.

    Filters (cheap first): must carry a bad-K2 edge, contain no K4, and be
    k-colorable (the degenerate gate — a non-k-colorable graph's "bad list" is
    just the constant list, i.e. plain chromatic obstruction, not a
    choosability-vs-chromatic gap). Survivors are then tested with the full
    choosability machinery.

    Each hit is a dict: {graph, bad_k2_edges, bad_list, critical}.
    """
    for g in graphs:
        cands = bad_k2_edges(g)
        if not cands or has_k4(g) or not is_k_colorable(g, k):
            continue
        bad = find_bad_list(g, k, palette=palette)
        if bad is None:  # genuinely k-choosable -> not a witness
            continue
        critical = all(
            find_bad_list(without_edge(g, e), k, palette=palette) is None
            for e in sorted(g.edges)
        )
        yield {
            "graph": g,
            "bad_k2_edges": cands,
            "bad_list": [sorted(s) for s in bad],
            "critical": critical,
        }
