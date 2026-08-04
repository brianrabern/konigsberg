"""CEGAR choosability: differential agreement with the exhaustive checker over
all small graphs, certificate re-verification, and symmetry-break invariance.

Skipped when python-sat isn't installed (optional `sat` extra).
"""
import pytest
from konigsberg_empirical.coloring import choosability as ch
from konigsberg_empirical.coloring.list_checks import is_k_choosable
from konigsberg_empirical.core import Graph
from konigsberg_empirical.search.enumerate import all_graphs

pytestmark = pytest.mark.skipif(not ch.is_available(), reason="python-sat not installed")


def complete(n: int) -> Graph:
    return Graph.of(n, [(i, j) for i in range(n) for j in range(i + 1, n)])


def cycle(n: int) -> Graph:
    return Graph.of(n, [(i, (i + 1) % n) for i in range(n)])


# --- textbook values ------------------------------------------------------

def test_triangle_not_2_choosable_but_3_choosable():
    assert ch.is_k_choosable_cegar(complete(3), 2) is False
    assert ch.is_k_choosable_cegar(complete(3), 3) is True


def test_even_cycle_2_choosable_odd_not():
    assert ch.is_k_choosable_cegar(cycle(4), 2) is True
    assert ch.is_k_choosable_cegar(cycle(5), 2) is False  # CEGAR handles n=5 easily


# --- certificates are independently re-checkable --------------------------

def test_found_bad_list_verifies():
    bad = ch.find_bad_list(complete(3), 2)
    assert bad is not None
    assert ch.verify_bad_list(complete(3), bad, 2) is True
    # and each list really has size k
    assert all(len(s) == 2 for s in bad)


def test_no_bad_list_when_choosable():
    assert ch.find_bad_list(complete(3), 3) is None


# --- differential: CEGAR vs the exhaustive checker over ALL small graphs --

@pytest.mark.parametrize("n", [1, 2, 3, 4])
def test_cegar_agrees_with_exhaustive_k2(n):
    for g in all_graphs(n):
        assert ch.is_k_choosable_cegar(g, 2) == is_k_choosable(g, 2)


def test_cegar_agrees_with_exhaustive_k3_small():
    for n in (1, 2, 3):
        for g in all_graphs(n):
            assert ch.is_k_choosable_cegar(g, 3) == is_k_choosable(g, 3)


# --- symmetry breaking must not change the verdict ------------------------

@pytest.mark.parametrize("n", [3, 4])
def test_symmetry_break_invariant(n):
    for g in all_graphs(n):
        with_sym = ch.is_k_choosable_cegar(g, 2, symmetry=True)
        without = ch.is_k_choosable_cegar(g, 2, symmetry=False)
        assert with_sym == without


# --- guards ---------------------------------------------------------------

def test_rejects_k_below_one():
    with pytest.raises(ValueError):
        ch.find_bad_list(complete(2), 0)


def test_palette_must_be_at_least_k():
    with pytest.raises(ValueError):
        ch.find_bad_list(complete(2), 3, palette=2)


def test_empty_graph_is_choosable():
    assert ch.find_bad_list(Graph.of(0, []), 3) is None
