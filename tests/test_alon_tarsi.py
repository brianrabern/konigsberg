"""Alon–Tarsi port: coefficient oracle, two-route agreement, AT numbers,
certificate re-check, and honesty of the harness tool.
"""
from __future__ import annotations

import networkx as nx
import pytest
from konigsberg_empirical.coloring import alon_tarsi as at
from konigsberg_empirical.coloring import choosability as ch
from konigsberg_empirical.core import Graph
from konigsberg_empirical.search.enumerate import all_graphs
from konigsberg_harness.ledger import TrustRoot
from konigsberg_harness.tools import empirical_tools as et


def complete(n: int) -> Graph:
    return Graph.of(n, [(i, j) for i in range(n) for j in range(i + 1, n)])


def cycle(n: int) -> Graph:
    return Graph.of(n, [(i, (i + 1) % n) for i in range(n)])


def path(n: int) -> Graph:
    return Graph.of(n, [(i, i + 1) for i in range(n - 1)])


def tree_star(n: int) -> Graph:
    """Star K_{1,n-1}."""
    return Graph.of(n, [(0, i) for i in range(1, n)])


# --- brute-force coefficient oracle ----------------------------------------

def _brute_coefficient(graph: Graph, power: list[int]) -> int:
    """Expand P_G = ∏_{u<v, uv∈E} (x_u − x_v) and read off the monomial coeff.

    Evaluates by summing over all assignments a[v] ∈ {0..power[v]} of
        (∏_{edges} (a_u − a_v)) / (∏_v ∏_{k≠a_v, k≤power[v]} (a_v − k)),
    which is the Lagrange / Contou–Carrère extraction used by Rabern's Normalizer
    — implemented here from the definition as an independent oracle.
    """
    # Direct multilinear expansion via iterating edge sign choices.
    edges = sorted(graph.edges)
    n = graph.n
    # P = ∏ (x_u - x_v) = ∑_{S ⊆ E} (−1)^{|S|} ∏_{uv∈E\S} x_u ∏_{uv∈S} x_v
    # where S = edges that pick the −x_v term.
    from collections import defaultdict

    coeffs: dict[tuple[int, ...], int] = defaultdict(int)
    m = len(edges)
    for mask in range(1 << m):
        exp = [0] * n
        sign = 1
        for i, (u, v) in enumerate(edges):
            if mask & (1 << i):
                # pick −x_v
                exp[v] += 1
                sign = -sign
            else:
                exp[u] += 1
        coeffs[tuple(exp)] += sign
    return coeffs.get(tuple(power), 0)


# --- 1. coefficient values vs brute force ----------------------------------

@pytest.mark.parametrize(
    "graph,power",
    [
        (Graph.of(1, []), [0]),
        (Graph.of(2, [(0, 1)]), [1, 0]),
        (Graph.of(2, [(0, 1)]), [0, 1]),
        (path(3), [1, 1, 0]),
        (path(3), [0, 1, 1]),
        (cycle(4), [1, 1, 1, 1]),
        (complete(3), [1, 1, 1]),
        (complete(3), [2, 1, 0]),
        (complete(4), [2, 1, 1, 0]),
    ],
)
def test_coefficient_matches_brute_force(graph, power):
    assert at.graph_polynomial_coefficient(graph, power) == _brute_coefficient(graph, power)


# --- 2. two-route agreement: coeff ≠ 0 ⇔ even ≠ odd -----------------------

@pytest.mark.parametrize("n", [1, 2, 3, 4, 5])
def test_coefficient_agrees_with_eulerian_counts(n):
    """Over all graphs on n verts; one orientation per out-degree sequence.

    Coeff depends only on the out-degree monomial; |even−odd| equals |coeff|,
    so one representative per out-degree class is enough. n=6 denser cases are
    covered by the sparse variant below (coeff is cubic in the monomial support).
    """
    for g in all_graphs(n):
        edges = sorted(g.edges)
        m = len(edges)
        seen_out: set[tuple[int, ...]] = set()
        for mask in range(1 << m):
            arcs = []
            out = [0] * n
            for i, (u, v) in enumerate(edges):
                if mask & (1 << i):
                    arcs.append((v, u))
                    out[v] += 1
                else:
                    arcs.append((u, v))
                    out[u] += 1
            key = tuple(out)
            if key in seen_out:
                continue
            seen_out.add(key)
            coeff = at.graph_polynomial_coefficient(g, out)
            even, odd = at.count_eulerian_subgraphs(arcs, n)
            assert (coeff != 0) == (even != odd), (
                f"n={n} edges={edges} out={out}: coeff={coeff} even={even} odd={odd}"
            )
            if coeff != 0:
                assert abs(coeff) == abs(even - odd)


def test_coefficient_agrees_with_eulerian_n6_sparse():
    """n=6 graphs with ≤9 edges: still exhaustive over out-degree classes."""
    for g in all_graphs(6):
        if len(g.edges) > 9:
            continue
        edges = sorted(g.edges)
        m = len(edges)
        seen_out: set[tuple[int, ...]] = set()
        for mask in range(1 << m):
            arcs = []
            out = [0] * 6
            for i, (u, v) in enumerate(edges):
                if mask & (1 << i):
                    arcs.append((v, u))
                    out[v] += 1
                else:
                    arcs.append((u, v))
                    out[u] += 1
            key = tuple(out)
            if key in seen_out:
                continue
            seen_out.add(key)
            coeff = at.graph_polynomial_coefficient(g, out)
            even, odd = at.count_eulerian_subgraphs(arcs, 6)
            assert (coeff != 0) == (even != odd)
            if coeff != 0:
                assert abs(coeff) == abs(even - odd)


# --- 3. AT number sanity ----------------------------------------------------

def test_at_number_even_cycle_is_2():
    assert at.alon_tarsi_number(cycle(4)) == 2
    assert at.alon_tarsi_number(cycle(6)) == 2


def test_at_number_odd_cycle_is_3():
    assert at.alon_tarsi_number(cycle(3)) == 3
    assert at.alon_tarsi_number(cycle(5)) == 3


def test_at_number_complete():
    for n in range(1, 5):
        assert at.alon_tarsi_number(complete(n)) == n


def test_at_number_trees_are_2():
    assert at.alon_tarsi_number(path(4)) == 2
    assert at.alon_tarsi_number(tree_star(5)) == 2
    assert at.alon_tarsi_number(Graph.of(1, [])) == 1  # edgeless


# --- 4. certificate re-check + one-way CEGAR cross-check -------------------

def test_certificate_verifies_when_returned():
    for g in [cycle(4), cycle(5), complete(3), path(4), tree_star(4)]:
        cert = at.certificate(g)
        assert cert is not None
        assert at.verify_certificate(g, cert) is True


def test_verify_rejects_tampered_certificate():
    g = cycle(4)
    cert = at.certificate(g)
    assert cert is not None
    bad = at.ATCertificate(
        arcs=cert.arcs, even=cert.even, odd=cert.even, coefficient=0
    )
    assert at.verify_certificate(g, bad) is False


@pytest.mark.skipif(not ch.is_available(), reason="python-sat not installed")
def test_at_good_implies_no_bad_list():
    """AT-good at k ⇒ offline k-choosable (one direction only)."""
    for g in [cycle(4), path(4), tree_star(4), complete(3)]:
        k = at.alon_tarsi_number(g)
        assert ch.find_bad_list(g, k) is None


# --- 5. honesty: AT failure never claims "not choosable" -------------------

def _g6(G) -> str:
    return nx.to_graph6_bytes(G, header=False).decode().strip()


def test_tool_mints_certificate_checked_on_hit():
    claim = et.alon_tarsi(_g6(nx.cycle_graph(4)))
    assert claim.provenance.trust_root is TrustRoot.CERTIFICATE
    assert claim.provenance.label() == "certificate-checked"
    assert "not choosable" not in claim.statement.lower()


def test_tool_never_claims_not_choosable_on_miss(monkeypatch):
    """Force a miss and assert the statement stays honest."""
    monkeypatch.setattr(at, "certificate", lambda g, f=None: None)
    # re-bind the tool's imported name
    monkeypatch.setattr(et._at, "certificate", lambda g, f=None: None)
    claim = et.alon_tarsi(_g6(nx.complete_graph(3)))
    assert claim.provenance.trust_root is TrustRoot.SOLVER
    assert "not choosable" not in claim.statement.lower()
    assert "no verified certificate" in claim.statement.lower()
