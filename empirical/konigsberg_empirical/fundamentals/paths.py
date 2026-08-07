"""Paths, distances, spanning trees."""
from __future__ import annotations

import networkx as nx

from ..core import Graph
from .codec import from_nx, to_nx


def neighbors(g: Graph, v: int) -> list[int]:
    if not (0 <= v < g.n):
        raise ValueError(f"vertex {v} out of range for n={g.n}")
    return sorted(g.neighbors(v))


def distance(g: Graph, u: int, v: int) -> int | None:
    G = to_nx(g)
    try:
        return int(nx.shortest_path_length(G, u, v))
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None


def shortest_path(g: Graph, u: int, v: int) -> list[int] | None:
    G = to_nx(g)
    try:
        return [int(x) for x in nx.shortest_path(G, u, v)]
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None


def bfs_order(g: Graph, root: int) -> list[int]:
    return [int(v) for v in nx.bfs_tree(to_nx(g), root)]


def dfs_order(g: Graph, root: int) -> list[int]:
    return [int(v) for v in nx.dfs_tree(to_nx(g), root)]


def spanning_tree(g: Graph) -> Graph:
    G = to_nx(g)
    if g.n == 0:
        return g
    if not nx.is_connected(G):
        # forest of spanning trees per component
        T = nx.Graph()
        T.add_nodes_from(G.nodes())
        for comp in nx.connected_components(G):
            H = G.subgraph(comp)
            T.add_edges_from(nx.minimum_spanning_tree(H).edges())
        return from_nx(T)
    return from_nx(nx.minimum_spanning_tree(G))
