"""Graph invariants — networkx-backed; witnesses for hard ones."""
from __future__ import annotations

import networkx as nx

from ..coloring.list_checks import clique_number_witness
from ..core import Graph
from .codec import to_nx


def order(g: Graph) -> int:
    return g.n


def size(g: Graph) -> int:
    return len(g.edges)


def degree_sequence(g: Graph) -> list[int]:
    return [g.degree(v) for v in range(g.n)]


def min_degree(g: Graph) -> int:
    degs = degree_sequence(g)
    return min(degs) if degs else 0


def max_degree(g: Graph) -> int:
    return g.max_degree


def average_degree(g: Graph) -> float:
    if g.n == 0:
        return 0.0
    return 2 * len(g.edges) / g.n


def density(g: Graph) -> float:
    if g.n < 2:
        return 0.0
    return 2 * len(g.edges) / (g.n * (g.n - 1))


def is_connected(g: Graph) -> bool:
    if g.n == 0:
        return True
    return nx.is_connected(to_nx(g))


def components(g: Graph) -> list[list[int]]:
    return [sorted(c) for c in nx.connected_components(to_nx(g))]


def num_components(g: Graph) -> int:
    return len(components(g))


def vertex_connectivity(g: Graph) -> int:
    if g.n == 0:
        return 0
    return int(nx.node_connectivity(to_nx(g)))


def edge_connectivity(g: Graph) -> int:
    if g.n == 0:
        return 0
    return int(nx.edge_connectivity(to_nx(g)))


def is_k_connected(g: Graph, k: int) -> bool:
    return vertex_connectivity(g) >= k


def is_bipartite(g: Graph) -> tuple[bool, list[list[int]] | None]:
    G = to_nx(g)
    if g.n == 0:
        return True, [[], []]
    try:
        color = nx.bipartite.color(G)
    except nx.NetworkXError:
        return False, None
    left = sorted(v for v, c in color.items() if c == 0)
    right = sorted(v for v, c in color.items() if c == 1)
    return True, [left, right]


def girth(g: Graph) -> int | None:
    """Shortest cycle length, or None if acyclic."""
    if g.n == 0 or not g.edges:
        return None
    G = to_nx(g)
    if nx.is_forest(G):
        return None
    return int(nx.girth(G))


def diameter(g: Graph) -> int | None:
    G = to_nx(g)
    if g.n == 0:
        return 0
    if not nx.is_connected(G):
        return None
    return int(nx.diameter(G))


def radius(g: Graph) -> int | None:
    G = to_nx(g)
    if g.n == 0:
        return 0
    if not nx.is_connected(G):
        return None
    return int(nx.radius(G))


def eccentricity(g: Graph) -> dict[int, int] | None:
    G = to_nx(g)
    if g.n == 0:
        return {}
    if not nx.is_connected(G):
        return None
    return {int(v): int(e) for v, e in nx.eccentricity(G).items()}


def is_tree(g: Graph) -> bool:
    return nx.is_tree(to_nx(g)) if g.n > 0 else True


def is_forest(g: Graph) -> bool:
    return nx.is_forest(to_nx(g))


def is_regular(g: Graph) -> bool:
    degs = degree_sequence(g)
    return len(set(degs)) <= 1


def is_planar(g: Graph) -> tuple[bool, list[int] | None]:
    """(planar?, Kuratowski subgraph vertices if not planar)."""
    G = to_nx(g)
    ok, cert = nx.check_planarity(G, counterexample=True)
    if ok:
        return True, None
    # cert is a Kuratowski subgraph
    verts = sorted(cert.nodes()) if cert is not None else None
    return False, verts


def is_eulerian(g: Graph) -> bool:
    return nx.is_eulerian(to_nx(g))


def has_eulerian_path(g: Graph) -> bool:
    return nx.has_eulerian_path(to_nx(g))


def triangle_count(g: Graph) -> int:
    return int(sum(nx.triangles(to_nx(g)).values()) // 3)


def transitivity(g: Graph) -> float:
    return float(nx.transitivity(to_nx(g)))


def degeneracy(g: Graph) -> tuple[int, list[int]]:
    """Return (degeneracy, elimination ordering). Ordering is a witness."""
    G = to_nx(g)
    if g.n == 0:
        return 0, []
    # core_number: degeneracy = max core number
    cores = nx.core_number(G)
    degner = max(cores.values()) if cores else 0
    # elimination order: repeatedly remove a min-degree vertex in the remaining graph
    H = G.copy()
    order: list[int] = []
    while H.number_of_nodes():
        v = min(H.nodes(), key=lambda u: H.degree(u))
        order.append(int(v))
        H.remove_node(v)
    return int(degner), order


def k_core_number(g: Graph) -> int:
    d, _ = degeneracy(g)
    return d


def independence_number(g: Graph) -> tuple[int, list[int]]:
    """α(G) + witnessing independent set (exact via clique on complement; small n)."""
    if g.n == 0:
        return 0, []
    # α(G) = ω(Ḡ)
    G = to_nx(g)
    comp = nx.complement(G)
    # reuse clique search on complement
    h = Graph.of(g.n, list(comp.edges()))
    omega, clique = clique_number_witness(h)
    return omega, clique


def verify_independent_set(g: Graph, verts: list[int]) -> bool:
    s = set(verts)
    return all(tuple(sorted((u, v))) not in g.edges for u in s for v in s if u < v)


def matching_number(g: Graph) -> tuple[int, list[list[int]]]:
    """ν(G) + witnessing matching (polynomial via max matching)."""
    G = to_nx(g)
    raw = nx.max_weight_matching(G, maxcardinality=True)
    # networkx: set of (u,v) edges, or mate dict u→v depending on version
    pairs = raw.items() if isinstance(raw, dict) else raw
    edges: list[list[int]] = []
    seen: set[tuple[int, int]] = set()
    for u, v in pairs:
        a, b = sorted((int(u), int(v)))
        if (a, b) not in seen:
            seen.add((a, b))
            edges.append([a, b])
    return len(edges), edges


def verify_matching(g: Graph, edges: list[list[int]]) -> bool:
    verts: set[int] = set()
    for e in edges:
        if len(e) != 2:
            return False
        a, b = int(e[0]), int(e[1])
        if tuple(sorted((a, b))) not in g.edges:
            return False
        if a in verts or b in verts:
            return False
        verts.add(a)
        verts.add(b)
    return True


def overview_named(g: Graph) -> str | None:
    """Best-effort named-graph match for small n (isomorphism to a WP1 family)."""
    from .construct import make_graph
    from .relations import is_isomorphic

    n = g.n
    candidates: list[tuple[str, Graph]] = []
    if n >= 1:
        candidates.append((f"K_{n}", make_graph("complete", n=n)))
        candidates.append((f"empty_{n}", make_graph("empty", n=n)))
        candidates.append((f"P_{n}", make_graph("path", n=n)))
    if n >= 3:
        candidates.append((f"C_{n}", make_graph("cycle", n=n)))
    if n >= 2:
        candidates.append((f"star_{n - 1}", make_graph("star", n=n - 1)))
    if n >= 4:
        candidates.append((f"W_{n}", make_graph("wheel", n=n)))
    if n == 10:
        candidates.append(("Petersen", make_graph("petersen")))
    # bipartite completes
    for a in range(1, n):
        b = n - a
        if a <= b:
            candidates.append((f"K_{{{a},{b}}}", make_graph("complete_bipartite", m=a, n=b)))

    for name, h in candidates:
        if is_isomorphic(g, h):
            return name
    return None
