"""Coloring primitives: ordinary coloring, given-list coloring, and exact
(small-graph) choosability, checked against textbook facts.
"""
import pytest
from konigsberg_empirical.coloring.list_checks import (
    chromatic_number,
    is_k_choosable,
    is_k_colorable,
    is_L_colorable,
)
from konigsberg_empirical.core import Graph


def complete(n: int) -> Graph:
    return Graph.of(n, [(i, j) for i in range(n) for j in range(i + 1, n)])


def cycle(n: int) -> Graph:
    return Graph.of(n, [(i, (i + 1) % n) for i in range(n)])


def path(n: int) -> Graph:
    return Graph.of(n, [(i, i + 1) for i in range(n - 1)])


# --- is_L_colorable -------------------------------------------------------

def test_L_colorable_true_when_lists_admit_a_proper_coloring():
    k3 = complete(3)
    assert is_L_colorable(k3, [{0, 1}, {1, 2}, {0, 2}]) is True


def test_L_colorable_false_when_lists_force_a_conflict():
    k3 = complete(3)  # a triangle with only two colors available cannot be colored
    assert is_L_colorable(k3, [{0, 1}, {0, 1}, {0, 1}]) is False


def test_L_colorable_rejects_wrong_number_of_lists():
    with pytest.raises(ValueError):
        is_L_colorable(complete(3), [{0, 1}, {0, 1}])


# --- is_k_colorable / chromatic_number ------------------------------------

def test_k_colorable_complete_graph():
    assert is_k_colorable(complete(4), 3) is False
    assert is_k_colorable(complete(4), 4) is True


def test_chromatic_number_textbook_values():
    assert chromatic_number(complete(4)) == 4
    assert chromatic_number(cycle(4)) == 2  # even cycle
    assert chromatic_number(cycle(5)) == 3  # odd cycle
    assert chromatic_number(path(5)) == 2
    assert chromatic_number(Graph.of(3, [])) == 1  # edgeless


# --- is_k_choosable (exact, small) ----------------------------------------

def test_choosability_edge_needs_two_colors():
    k2 = complete(2)
    assert is_k_choosable(k2, 1) is False
    assert is_k_choosable(k2, 2) is True


def test_triangle_not_2_choosable_but_3_choosable():
    k3 = complete(3)
    assert is_k_choosable(k3, 2) is False
    assert is_k_choosable(k3, 3) is True


def test_path_is_2_choosable():
    assert is_k_choosable(path(3), 2) is True


def test_even_cycle_is_2_choosable():
    assert is_k_choosable(cycle(4), 2) is True


def test_choosability_guard_refuses_oversized_search():
    with pytest.raises(ValueError):
        is_k_choosable(cycle(5), 2)  # 45**4 assignments exceeds the default guard


def test_choosability_guard_respects_custom_limit():
    # a case that normally runs (84**2 assignments) is refused under a low ceiling
    with pytest.raises(ValueError):
        is_k_choosable(complete(3), 3, limit=100)
