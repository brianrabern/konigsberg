"""graph6 codec + canonical labeling (nauty labelg when available)."""
from __future__ import annotations

import shutil
import subprocess
from typing import Any

import networkx as nx

from ..core import Graph
from ..search.enumerate import parse_graph6


def to_nx(graph: Graph) -> nx.Graph:
    G = nx.Graph()
    G.add_nodes_from(range(graph.n))
    G.add_edges_from(graph.edges)
    return G


def from_nx(G: nx.Graph) -> Graph:
    """Relabel nodes to 0..n-1 in sorted order; reject loops/multiedges."""
    if G.is_directed() or G.is_multigraph():
        raise ValueError("only undirected simple graphs are supported")
    nodes = sorted(G.nodes())
    relabel = {v: i for i, v in enumerate(nodes)}
    edges = []
    for u, v in G.edges():
        if u == v:
            raise ValueError("loops are not allowed")
        a, b = relabel[u], relabel[v]
        edges.append((a, b))
    return Graph.of(len(nodes), edges)


def to_graph6(graph: Graph) -> str:
    """Encode as graph6 (no header). Not necessarily canonical."""
    return nx.to_graph6_bytes(to_nx(graph), header=False).decode().strip()


def graph6_encode(n: int, edges: list[tuple[int, int] | list[int]]) -> str:
    """Encode n + edge list as graph6. Validates simple-graph constraints."""
    norm = [(int(e[0]), int(e[1])) for e in edges]
    return to_graph6(Graph.of(n, norm))


def graph6_decode(s: str) -> dict[str, Any]:
    """Decode graph6 → {n, edges} (edges as sorted [u,v] lists)."""
    g = parse_graph6(s)
    return {"n": g.n, "edges": [list(e) for e in sorted(g.edges)]}


def _find_labelg() -> str | None:
    for name in ("labelg", "nauty-labelg"):
        path = shutil.which(name)
        if path:
            return path
    return None


def canonical_graph6(graph: Graph) -> str:
    """Return a canonical graph6 string for ``graph``.

    Prefer nauty ``labelg`` when on PATH (true canonical labeling). Otherwise
    use a deterministic degree-then-WL-hash ordered relabeling — near-canonical
    for dedup, **not** provably canonical. Exact identity still needs
    ``is_isomorphic``.
    """
    raw = to_graph6(graph)
    labelg = _find_labelg()
    if labelg is not None:
        proc = subprocess.run(
            [labelg, "-q"],
            input=raw + "\n",
            text=True,
            capture_output=True,
            check=False,
        )
        out = (proc.stdout or "").strip().splitlines()
        if proc.returncode == 0 and out:
            return out[0].strip()
    # Fallback: sort vertices by (degree, WL-ish local structure via neighbor deg multiset)
    G = to_nx(graph)
    if graph.n == 0:
        return raw
    # Stable key: degree, sorted neighbor-degree tuple, then original label
    def key(v: int) -> tuple:
        nbrs = sorted(G.neighbors(v))
        return (G.degree(v), tuple(sorted(G.degree(u) for u in nbrs)), v)

    order = sorted(range(graph.n), key=key)
    mapping = {old: new for new, old in enumerate(order)}
    H = nx.relabel_nodes(G, mapping, copy=True)
    return nx.to_graph6_bytes(H, header=False).decode().strip()


def canonical_graph6_str(s: str) -> str:
    return canonical_graph6(parse_graph6(s))
