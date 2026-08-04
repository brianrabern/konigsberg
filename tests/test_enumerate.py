"""Enumeration: graph6 parsing (vs networkx oracle) + atlas counts/constraints.

The geng backend is not exercised here (nauty may be absent); its correctness
rests on parse_graph6, which IS tested against networkx's own graph6 writer, and
on _matches, tested via the atlas path. Differential tests against geng belong in
tests/differential once nauty is in the CI image.
"""
import networkx as nx
import pytest
from konigsberg_empirical.core import Graph
from konigsberg_empirical.search.enumerate import all_graphs, parse_graph6


def _edgeset(g: Graph) -> set[tuple[int, int]]:
    return set(g.edges)


def _nx_edgeset(G) -> set[tuple[int, int]]:
    return {tuple(sorted(e)) for e in G.edges()}


# --- parse_graph6 vs networkx oracle --------------------------------------

@pytest.mark.parametrize(
    "G",
    [
        nx.empty_graph(1),
        nx.empty_graph(5),
        nx.path_graph(4),
        nx.cycle_graph(5),
        nx.complete_graph(6),
        nx.star_graph(5),  # 6 nodes
        nx.petersen_graph(),  # 10 nodes, nontrivial
    ],
)
def test_parse_graph6_matches_networkx(G):
    g6 = nx.to_graph6_bytes(G, header=False).decode().strip()
    parsed = parse_graph6(g6)
    assert parsed.n == G.number_of_nodes()
    assert _edgeset(parsed) == _nx_edgeset(G)


def test_parse_graph6_rejects_empty():
    with pytest.raises(ValueError):
        parse_graph6("   ")


# --- all_graphs counts (atlas fallback) -----------------------------------

@pytest.mark.parametrize(
    "n,expected",
    [(0, 1), (1, 1), (2, 2), (3, 4), (4, 11), (5, 34), (6, 156), (7, 1044)],
)
def test_all_graphs_counts_non_isomorphic(n, expected):
    assert sum(1 for _ in all_graphs(n)) == expected


def test_all_graphs_connected_constraint():
    # connected graphs: n=2 ->1, n=3 ->2, n=4 ->6
    assert sum(1 for _ in all_graphs(4, constraints={"connected": True})) == 6
    assert sum(1 for _ in all_graphs(3, constraints={"connected": True})) == 2


def test_all_graphs_edge_bounds():
    # graphs on 4 vertices with exactly 3 edges: triangle+isolated, path P4, star K1,3
    got = list(all_graphs(4, constraints={"min_edges": 3, "max_edges": 3}))
    assert len(got) == 3
    assert all(len(g.edges) == 3 for g in got)


def test_all_graphs_degree_constraint_yields_regular_only():
    # max_degree<=1 on 4 vertices == matchings: empty, single edge, perfect matching
    got = list(all_graphs(4, constraints={"max_degree": 1}))
    assert len(got) == 3
    assert all(g.max_degree <= 1 for g in got)


def test_all_graphs_raises_beyond_atlas_without_geng():
    from konigsberg_empirical.search import enumerate as en

    if en._find_geng() is not None:
        pytest.skip("geng present; atlas ceiling does not apply")
    with pytest.raises(RuntimeError):
        list(all_graphs(8))


def test_all_graphs_rejects_negative_n():
    with pytest.raises(ValueError):
        list(all_graphs(-1))
