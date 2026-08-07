"""Relations between graphs: isomorphism, subgraph, containment."""
from __future__ import annotations

import networkx as nx
from networkx.algorithms import isomorphism as iso

from ..coloring.list_checks import find_clique, verify_clique
from ..core import Graph
from .codec import to_nx
from .invariants import (
    degree_sequence,
    is_connected,
    num_components,
    order,
    size,
)


def is_isomorphic(g: Graph, h: Graph) -> bool:
    return nx.is_isomorphic(to_nx(g), to_nx(h))


def could_be_isomorphic(g: Graph, h: Graph) -> bool:
    """Fast invariant pre-check; True does not imply isomorphic."""
    if order(g) != order(h) or size(g) != size(h):
        return False
    if sorted(degree_sequence(g), reverse=True) != sorted(degree_sequence(h), reverse=True):
        return False
    if is_connected(g) != is_connected(h):
        return False
    return num_components(g) == num_components(h)


def is_subgraph(host: Graph, pattern: Graph) -> tuple[bool, dict[int, int] | None]:
    """Pattern embeds as (not necessarily induced) subgraph of host.

    Returns (ok, embedding) where embedding maps pattern vertex → host vertex.
    """
    if pattern.n > host.n or len(pattern.edges) > len(host.edges):
        return False, None
    matcher = iso.GraphMatcher(to_nx(host), to_nx(pattern))
    try:
        m = next(matcher.subgraph_isomorphisms_iter())
    except StopIteration:
        return False, None
    # m: host_vertex -> pattern_vertex
    emb = {int(p): int(h) for h, p in m.items()}
    return True, emb


def is_induced_subgraph(host: Graph, pattern: Graph) -> tuple[bool, dict[int, int] | None]:
    if pattern.n > host.n:
        return False, None
    matcher = iso.GraphMatcher(to_nx(host), to_nx(pattern))
    for m in matcher.subgraph_isomorphisms_iter():
        emb = {int(p): int(h) for h, p in m.items()}
        host_verts = [emb[i] for i in range(pattern.n)]
        induced_edges = {
            tuple(sorted((host_verts[i], host_verts[j])))
            for i in range(pattern.n)
            for j in range(i + 1, pattern.n)
            if tuple(sorted((host_verts[i], host_verts[j]))) in host.edges
        }
        pattern_edges = {tuple(sorted((emb[u], emb[v]))) for u, v in pattern.edges}
        if induced_edges == pattern_edges:
            return True, emb
    return False, None


def contains_clique(g: Graph, k: int) -> tuple[bool, list[int] | None]:
    if k <= 0:
        return True, []
    c = find_clique(g, k)
    if c is not None and verify_clique(g, c):
        return True, c
    return False, None


def contains_cycle(g: Graph, length: int | None = None) -> tuple[bool, list[int] | None]:
    G = to_nx(g)
    if length is None:
        try:
            cyc = nx.find_cycle(G, orientation="ignore")
            verts: list[int] = []
            for u, v, *_rest in cyc:
                if not verts:
                    verts.append(int(u))
                verts.append(int(v))
            if len(verts) > 1 and verts[0] == verts[-1]:
                verts = verts[:-1]
            return True, verts
        except nx.NetworkXNoCycle:
            return False, None
    for cyc in nx.simple_cycles(G):
        if len(cyc) == length and len(set(cyc)) == length:
            return True, [int(v) for v in cyc]
    return False, None


def contains_path(g: Graph, length: int) -> tuple[bool, list[int] | None]:
    """Path with ``length`` edges (length+1 vertices)."""
    need = length + 1
    if need > g.n or length < 0:
        return False, None
    if length == 0:
        return (True, [0]) if g.n else (False, None)
    G = to_nx(g)
    for start in range(g.n):
        stack: list[tuple[int, list[int]]] = [(start, [start])]
        while stack:
            u, path = stack.pop()
            if len(path) - 1 == length:
                return True, path
            for v in G.neighbors(u):
                if v not in path:
                    stack.append((int(v), path + [int(v)]))
    return False, None


# Minor containment (branch-set models). Small-graph exhaustive search.
_MINOR_HOST_MAX = 16
_MINOR_PATTERN_MAX = 7


def _induced_connected(g_adj: list[set[int]], verts: list[int]) -> bool:
    if not verts:
        return False
    s = set(verts)
    start = verts[0]
    seen = {start}
    stack = [start]
    while stack:
        u = stack.pop()
        for w in g_adj[u]:
            if w in s and w not in seen:
                seen.add(w)
                stack.append(w)
    return len(seen) == len(s)


def _branch_cross(g_adj: list[set[int]], a: list[int], b: list[int]) -> bool:
    bset = set(b)
    for u in a:
        if g_adj[u] & bset:
            return True
    return False


def verify_minor_model(
    host: Graph, pattern: Graph, branch_sets: list[list[int]]
) -> bool:
    """Re-check a branch-set witness that ``pattern`` is a minor of ``host``."""
    if len(branch_sets) != pattern.n:
        return False
    g_adj = [set(host.neighbors(v)) for v in range(host.n)]
    seen: set[int] = set()
    for branch in branch_sets:
        if not branch or not _induced_connected(g_adj, branch):
            return False
        for v in branch:
            if not (0 <= v < host.n) or v in seen:
                return False
            seen.add(v)
    for u, v in pattern.edges:
        if not _branch_cross(g_adj, branch_sets[u], branch_sets[v]):
            return False
    return True


def contains_minor(
    host: Graph, pattern: Graph
) -> tuple[bool, list[list[int]] | None]:
    """Decide whether ``pattern`` is a minor of ``host``.

    Returns ``(True, branch_sets)`` where ``branch_sets[i]`` is the connected
    branch set in ``host`` for pattern vertex ``i``, or ``(False, None)``.

    Exhaustive search for small instances (host n≤16, pattern n≤7). A subgraph
    embedding is a minor with singleton branch sets — but the converse is false:
    ``is_subgraph=False`` does **not** imply ``contains_minor=False``.
    """
    if pattern.n > host.n:
        return False, None
    if pattern.n == 0:
        return True, []
    if host.n > _MINOR_HOST_MAX:
        raise ValueError(
            f"contains_minor: host n={host.n} exceeds limit {_MINOR_HOST_MAX} "
            "(exhaustive branch-set search)"
        )
    if pattern.n > _MINOR_PATTERN_MAX:
        raise ValueError(
            f"contains_minor: pattern n={pattern.n} exceeds limit {_MINOR_PATTERN_MAX}"
        )

    # Fast path: subgraph ⇒ minor with singleton branches.
    ok, emb = is_subgraph(host, pattern)
    if ok and emb is not None:
        model = [[emb[i]] for i in range(pattern.n)]
        if verify_minor_model(host, pattern, model):
            return True, model

    g_adj = [set(host.neighbors(v)) for v in range(host.n)]
    h_edges = list(pattern.edges)
    sets: list[list[int] | None] = [None] * pattern.n
    order = sorted(
        range(pattern.n),
        key=lambda v: -sum(1 for a, b in h_edges if v in (a, b)),
    )

    def partial_ok() -> bool:
        for u, v in h_edges:
            su, sv = sets[u], sets[v]
            if su is not None and sv is not None and not _branch_cross(g_adj, su, sv):
                return False
        return True

    def rec(oi: int, remaining: set[int]) -> bool:
        if oi == len(order):
            return True
        hv = order[oi]
        rem = list(remaining)
        n = len(rem)
        need_after = len(order) - oi - 1
        for mask in range(1, 1 << n):
            verts = [rem[i] for i in range(n) if mask & (1 << i)]
            if n - len(verts) < need_after:
                continue
            if not _induced_connected(g_adj, verts):
                continue
            sets[hv] = verts
            if partial_ok() and rec(oi + 1, remaining - set(verts)):
                return True
            sets[hv] = None
        return False

    if rec(0, set(range(host.n))):
        model = [list(s) for s in sets]  # type: ignore[arg-type]
        if not verify_minor_model(host, pattern, model):
            raise RuntimeError("minor search returned a non-certificate")
        return True, model
    return False, None
