"""SAT coloring layer: textbook values, differential agreement with the pure
backtracking checker, and SAT as a drop-in choosability inner check.

Skipped entirely when python-sat isn't installed (it's the optional `sat` extra).
"""
import pytest
from konigsberg_empirical.coloring.list_checks import (
    is_k_choosable,
    is_k_colorable,
    is_L_colorable,
)
from konigsberg_empirical.core import Graph
from konigsberg_empirical.search import sat
from konigsberg_empirical.search.enumerate import all_graphs

pytestmark = pytest.mark.skipif(not sat.is_available(), reason="python-sat not installed")


def complete(n: int) -> Graph:
    return Graph.of(n, [(i, j) for i in range(n) for j in range(i + 1, n)])


def cycle(n: int) -> Graph:
    return Graph.of(n, [(i, (i + 1) % n) for i in range(n)])


# --- textbook values ------------------------------------------------------

def test_sat_k_colorable_complete_graph():
    assert sat.sat_k_colorable(complete(4), 3) is False
    assert sat.sat_k_colorable(complete(4), 4) is True


def test_sat_k_colorable_odd_cycle_needs_three():
    assert sat.sat_k_colorable(cycle(5), 2) is False
    assert sat.sat_k_colorable(cycle(5), 3) is True


def test_sat_L_colorable_matches_definition():
    k3 = complete(3)
    assert sat.sat_L_colorable(k3, [{0, 1}, {1, 2}, {0, 2}]) is True
    assert sat.sat_L_colorable(k3, [{0, 1}, {0, 1}, {0, 1}]) is False


def test_sat_L_colorable_empty_list_is_unsat():
    assert sat.sat_L_colorable(complete(2), [set(), {0, 1}]) is False


def test_sat_L_colorable_rejects_wrong_length():
    with pytest.raises(ValueError):
        sat.sat_L_colorable(complete(3), [{0, 1}])


# --- differential: SAT vs pure backtracking, over ALL small graphs --------

@pytest.mark.parametrize("n", [1, 2, 3, 4, 5])
@pytest.mark.parametrize("k", [2, 3])
def test_sat_agrees_with_backtracking_k_colorability(n, k):
    for g in all_graphs(n):
        assert sat.sat_k_colorable(g, k) == is_k_colorable(g, k)


@pytest.mark.parametrize("n", [3, 4])
def test_sat_agrees_with_backtracking_on_given_lists(n):
    # exercise sat_L_colorable vs is_L_colorable on a fixed 2-list assignment
    for g in all_graphs(n):
        lists = [{i % 2, (i + 1) % 2 + 1} for i in range(n)]  # size-2 lists
        assert sat.sat_L_colorable(g, lists) == is_L_colorable(g, lists)


# --- SAT as the choosability inner check ----------------------------------

def test_choosability_same_verdict_with_sat_backend():
    # identical answers whether the inner check is backtracking or SAT
    for g, k in [(complete(2), 2), (complete(3), 2), (complete(3), 3), (cycle(4), 2)]:
        pure = is_k_choosable(g, k)
        via_sat = is_k_choosable(g, k, colorable=sat.sat_L_colorable)
        assert pure == via_sat
