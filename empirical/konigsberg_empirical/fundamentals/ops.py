"""Structural operations: Graph → Graph."""
from __future__ import annotations

import networkx as nx

from ..core import Graph
from .codec import from_nx, to_nx


def complement(g: Graph) -> Graph:
    return from_nx(nx.complement(to_nx(g)))


def induced_subgraph(g: Graph, vertices: list[int]) -> Graph:
    vs = sorted({int(v) for v in vertices})
    for v in vs:
        if not (0 <= v < g.n):
            raise ValueError(f"vertex {v} out of range for n={g.n}")
    H = to_nx(g).subgraph(vs).copy()
    return from_nx(H)


def delete_vertices(g: Graph, vertices: list[int]) -> Graph:
    drop = {int(v) for v in vertices}
    keep = [v for v in range(g.n) if v not in drop]
    return induced_subgraph(g, keep)


def delete_vertex(g: Graph, v: int) -> Graph:
    return delete_vertices(g, [v])


def delete_edges(g: Graph, edges: list[list[int] | tuple[int, int]]) -> Graph:
    drop = {tuple(sorted((int(e[0]), int(e[1])))) for e in edges}
    return Graph.of(g.n, [e for e in g.edges if e not in drop])


def delete_edge(g: Graph, u: int, v: int) -> Graph:
    return delete_edges(g, [[u, v]])


def add_edge(g: Graph, u: int, v: int) -> Graph:
    u, v = int(u), int(v)
    if not (0 <= u < g.n and 0 <= v < g.n) or u == v:
        raise ValueError(f"bad edge ({u},{v}) for n={g.n}")
    return Graph.of(g.n, list(g.edges) + [(u, v)])


def add_vertex(g: Graph) -> Graph:
    return Graph.of(g.n + 1, list(g.edges))


def contract_edge(g: Graph, u: int, v: int) -> Graph:
    G = to_nx(g)
    H = nx.contracted_edge(G, (u, v), self_loops=False)
    return from_nx(H)


def line_graph(g: Graph) -> Graph:
    return from_nx(nx.line_graph(to_nx(g)))


def disjoint_union(g: Graph, h: Graph) -> Graph:
    return from_nx(nx.disjoint_union(to_nx(g), to_nx(h)))


def union(g: Graph, h: Graph) -> Graph:
    if g.n != h.n:
        raise ValueError("union requires same vertex set size")
    return Graph.of(g.n, list(g.edges | h.edges))


def join(g: Graph, h: Graph) -> Graph:
    """Zykov join G ∨ H: disjoint union plus every cross edge V(G)—V(H).

    NetworkX has no ``nx.join`` (Eva hit AttributeError on the join tool).
    """
    n_g = g.n
    u = nx.disjoint_union(to_nx(g), to_nx(h))
    u.add_edges_from((i, n_g + j) for i in range(g.n) for j in range(h.n))
    return from_nx(u)


def cartesian_product(g: Graph, h: Graph) -> Graph:
    return from_nx(nx.cartesian_product(to_nx(g), to_nx(h)))


def tensor_product(g: Graph, h: Graph) -> Graph:
    return from_nx(nx.tensor_product(to_nx(g), to_nx(h)))


def k_core(g: Graph, k: int) -> Graph:
    H = nx.k_core(to_nx(g), k)
    return from_nx(H)


def mycielskian(g: Graph) -> Graph:
    """Mycielskian μ(G): raises χ by one while keeping the clique number fixed
    (triangle-free ⇒ triangle-free). μ(C₅) is the Grötzsch graph; iterating from
    K₂ builds the triangle-free k-chromatic family."""
    return from_nx(nx.mycielskian(to_nx(g)))


def blow_up(g: Graph, r: int, clique: bool = True) -> Graph:
    """Blow up each vertex into r copies (lexicographic product G[·]).

    clique=True  → each vertex becomes a Kᵣ (clique blow-up G[Kᵣ]).
    clique=False → each vertex becomes an independent set (blow-up G[K̄ᵣ]).
    Adjacent vertices' copies are fully joined either way.
    """
    r = int(r)
    if r < 1:
        raise ValueError(f"blow-up factor r must be ≥ 1, got {r}")
    inner = nx.complete_graph(r) if clique else nx.empty_graph(r)
    return from_nx(nx.lexicographic_product(to_nx(g), inner))
