"""BK-attack helpers: bad-K2 detection, K4 filter, edge deletion, and
choice-criticality (validated on C5, which is certainly 2-choice-critical).

Predicate tests run without SAT; choosability-dependent tests skip without it.
"""
import pytest
from konigsberg_empirical.coloring import bk
from konigsberg_empirical.coloring import choosability as ch
from konigsberg_empirical.core import Graph

needs_sat = pytest.mark.skipif(not ch.is_available(), reason="python-sat not installed")


def complete(n: int) -> Graph:
    return Graph.of(n, [(i, j) for i in range(n) for j in range(i + 1, n)])


def cycle(n: int) -> Graph:
    return Graph.of(n, [(i, (i + 1) % n) for i in range(n)])


def path(n: int) -> Graph:
    return Graph.of(n, [(i, i + 1) for i in range(n - 1)])


def bad_k2_gadget() -> Graph:
    """Two adjacent degree-4 vertices (0,1); six degree-3 outer vertices; no K4."""
    edges = [
        (0, 1),
        (0, 2), (0, 3), (0, 4),
        (1, 5), (1, 6), (1, 7),
        (2, 5), (3, 6), (4, 7),  # outer +1
        (2, 6), (3, 7), (4, 5),  # outer +1 -> each outer degree 3
    ]
    return Graph.of(8, edges)


# --- pure predicates (no SAT) ---------------------------------------------

def test_bad_k2_edges_finds_the_edge():
    g = bad_k2_gadget()
    assert g.degree(0) == 4 and g.degree(1) == 4
    assert bk.bad_k2_edges(g) == [(0, 1)]


def test_bad_k2_edges_empty_when_no_degree4():
    assert bk.bad_k2_edges(cycle(5)) == []  # all degree 2


def test_has_k4():
    assert bk.has_k4(complete(4)) is True
    assert bk.has_k4(cycle(5)) is False
    assert bk.has_k4(bad_k2_gadget()) is False


def test_without_edge_removes_exactly_one():
    g = complete(4)
    h = bk.without_edge(g, (0, 1))
    assert (0, 1) not in h.edges
    assert len(h.edges) == len(g.edges) - 1
    assert h.n == g.n


# --- choice-criticality (needs SAT) ---------------------------------------

@needs_sat
def test_c5_is_2_choice_critical():
    # odd cycle: not 2-choosable, but every edge-deletion is a 2-choosable path
    assert bk.is_choice_critical(cycle(5), k=2) is True


@needs_sat
def test_path_is_not_critical_because_it_is_choosable():
    assert bk.is_choice_critical(path(5), k=2) is False


@needs_sat
def test_even_cycle_not_critical():
    assert bk.is_choice_critical(cycle(4), k=2) is False


# --- scan (needs SAT) -----------------------------------------------------

@needs_sat
def test_scan_skips_graphs_without_bad_k2():
    # K4 has no degree-4 vertices and contains K4 -> filtered out, no hits
    assert list(bk.find_bad_k2_critical([complete(4)], k=3)) == []


@needs_sat
def test_scan_runs_and_shapes_hits():
    # feed the gadget; assert it runs and any hit has the expected shape.
    # small palette keeps the n=8 search fast (heuristic mode, as in bk2.py).
    hits = list(bk.find_bad_k2_critical([bad_k2_gadget()], k=3, palette=4))
    for h in hits:
        assert set(h) == {"graph", "bad_k2_edges", "bad_list", "critical"}
        assert h["bad_k2_edges"] == [(0, 1)]
