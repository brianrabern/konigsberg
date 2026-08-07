"""Graph fundamentals: construction, describe, invariants, structure, relations."""
from __future__ import annotations

import re

import pytest
from konigsberg_empirical.fundamentals import invariants as inv
from konigsberg_empirical.fundamentals import ops
from konigsberg_empirical.fundamentals import relations as rel
from konigsberg_empirical.fundamentals.codec import (
    canonical_graph6,
    graph6_decode,
    graph6_encode,
)
from konigsberg_empirical.fundamentals.construct import make_graph as build
from konigsberg_empirical.fundamentals.inspect import describe
from konigsberg_harness.ledger import TrustRoot
from konigsberg_harness.tools.fundamentals_tools import FUNDAMENTAL_TOOL_NAMES
from konigsberg_harness.tools.registry import build_registry


def _g6_from_claim(claim) -> str:
    m = re.search(r"graph6=(\S+)", claim.statement)
    assert m, claim.statement
    return m.group(1).rstrip(")")


# --- empirical layer ------------------------------------------------------


def test_make_complete_4_canonical():
    g = build("complete", n=4)
    assert canonical_graph6(g) == "C~"
    assert g.n == 4 and len(g.edges) == 6


def test_from_edges_roundtrip_codec():
    edges = [[0, 1], [1, 2], [2, 0]]
    s = graph6_encode(3, edges)
    data = graph6_decode(s)
    assert data["n"] == 3
    assert sorted(tuple(e) for e in data["edges"]) == [(0, 1), (0, 2), (1, 2)]


def test_from_graph6_c_tilde():
    g = build("from_graph6", graph6="C~")
    assert g.n == 4 and len(g.edges) == 6


def test_describe_k4():
    d = describe(build("from_graph6", graph6="C~"))
    assert d["n"] == 4 and d["m"] == 6
    assert d["is_regular"] and d["connected"]
    assert d["bipartite"] is False
    assert d["girth"] == 3
    assert d["is_planar"] is True
    assert d["named"] in ("K_4", "K₄")


def test_petersen_invariants():
    g = build("petersen")
    assert inv.min_degree(g) == inv.max_degree(g) == 3
    assert inv.girth(g) == 5
    alpha, ind = inv.independence_number(g)
    assert alpha == 4 and inv.verify_independent_set(g, ind)
    from konigsberg_empirical.coloring.list_checks import clique_number_witness

    omega, clique = clique_number_witness(g)
    assert omega == 2 and len(clique) == 2
    d, _ = inv.degeneracy(g)
    assert d == 3
    planar, _ = inv.is_planar(g)
    assert planar is False
    assert inv.vertex_connectivity(g) == 3


def test_c5_and_k33():
    c5 = build("cycle", n=5)
    assert inv.is_bipartite(c5)[0] is False
    assert inv.girth(c5) == 5
    k33 = build("complete_bipartite", m=3, n=3)
    assert inv.is_bipartite(k33)[0] is True
    assert inv.is_planar(k33)[0] is False


def test_complement_line_contract_induced():
    k4 = build("complete", n=4)
    empty4 = ops.complement(k4)
    assert empty4.n == 4 and len(empty4.edges) == 0
    lg = ops.line_graph(k4)
    assert lg.n == 6
    contracted = ops.contract_edge(k4, 0, 1)
    assert contracted.n == 3
    ind = ops.induced_subgraph(k4, [0, 1, 2])
    assert ind.n == 3 and len(ind.edges) == 3


def test_isomorphism_and_clique_witness():
    c5a = build("cycle", n=5)
    edges = [[1, 2], [2, 3], [3, 4], [4, 0], [0, 1]]
    c5b = build("from_edges", n=5, edges=edges)
    assert rel.is_isomorphic(c5a, c5b)
    ok, wit = rel.contains_clique(build("complete", n=4), 3)
    assert ok and wit is not None and len(wit) == 3


def test_petersen_has_k5_and_k33_minors_not_as_subgraphs():
    pet = build("petersen")
    k5 = build("complete", n=5)
    k33 = build("complete_bipartite", m=3, n=3)
    assert rel.is_subgraph(pet, k5)[0] is False
    assert rel.is_subgraph(pet, k33)[0] is False
    ok5, br5 = rel.contains_minor(pet, k5)
    assert ok5 and br5 is not None
    assert rel.verify_minor_model(pet, k5, br5)
    ok33, br33 = rel.contains_minor(pet, k33)
    assert ok33 and br33 is not None
    assert rel.verify_minor_model(pet, k33, br33)


def test_tree_has_no_k3_minor():
    t = build("path", n=4)
    k3 = build("complete", n=3)
    ok, br = rel.contains_minor(t, k3)
    assert ok is False and br is None


# --- harness tools --------------------------------------------------------


def test_registry_includes_fundamentals():
    reg = build_registry()
    names = set(reg.names())
    assert FUNDAMENTAL_TOOL_NAMES <= names
    assert "make_graph" in names and "describe_graph" in names


def test_make_graph_tool_mints_k4():
    reg = build_registry()
    claim = reg.dispatch("make_graph", {"kind": "complete", "n": 4})
    assert "C~" in claim.statement
    assert claim.provenance.trust_root is TrustRoot.ENUMERATION


def test_describe_graph_tool():
    reg = build_registry()
    claim = reg.dispatch("describe_graph", {"graph6": "C~"})
    assert "n=4" in claim.statement and "m=6" in claim.statement
    assert "named=K_4" in claim.statement or "K_4" in claim.statement


def test_independence_and_matching_witnesses():
    reg = build_registry()
    pet = reg.dispatch("make_graph", {"kind": "petersen"})
    g6 = _g6_from_claim(pet)
    alpha = reg.dispatch("independence_number", {"graph6": g6})
    assert "α=4" in alpha.statement
    assert alpha.provenance.trust_root is TrustRoot.CERTIFICATE
    matching = reg.dispatch("matching_number", {"graph6": g6})
    assert matching.provenance.trust_root is TrustRoot.CERTIFICATE
    assert "ν=" in matching.statement


def test_structure_complement_via_tools():
    reg = build_registry()
    k4 = reg.dispatch("make_graph", {"kind": "complete", "n": 4})
    g6 = _g6_from_claim(k4)
    comp = reg.dispatch("complement", {"graph6": g6})
    out = _g6_from_claim(comp)
    decoded = graph6_decode(out)
    assert decoded["n"] == 4 and decoded["edges"] == []


def test_isomorphic_c5_via_tools():
    reg = build_registry()
    a = _g6_from_claim(reg.dispatch("make_graph", {"kind": "cycle", "n": 5}))
    b = _g6_from_claim(
        reg.dispatch(
            "make_graph",
            {
                "kind": "from_edges",
                "n": 5,
                "edges": [[1, 2], [2, 3], [3, 4], [4, 0], [0, 1]],
            },
        )
    )
    claim = reg.dispatch("is_isomorphic", {"graph6": a, "other": b})
    assert "True" in claim.statement


def test_contains_minor_tool_petersen_k5():
    reg = build_registry()
    pet = _g6_from_claim(reg.dispatch("make_graph", {"kind": "petersen"}))
    k5 = _g6_from_claim(reg.dispatch("make_graph", {"kind": "complete", "n": 5}))
    # Wrong proxy would be is_subgraph=False → over-conclude no K5 minor.
    sub = reg.dispatch("is_subgraph", {"host": pet, "pattern": k5})
    assert "False" in sub.statement
    minor = reg.dispatch("contains_minor", {"host": pet, "pattern": k5})
    assert "True" in minor.statement
    assert "branch sets" in minor.statement
    assert minor.provenance.trust_root is TrustRoot.CERTIFICATE


def test_grouped_tool_specs_has_construction():
    reg = build_registry()
    groups = dict(reg.grouped_tool_specs())
    assert "construction" in groups
    names = {s["name"] for s in groups["construction"]}
    assert {"make_graph", "graph6_encode", "graph6_decode"} <= names
    assert "coloring" in groups
    rel_names = {s["name"] for s in groups["relations"]}
    assert "contains_minor" in rel_names


def test_make_graph_args_validated():
    from pydantic import ValidationError

    reg = build_registry()
    with pytest.raises(ValidationError):
        reg.dispatch("make_graph", {})  # missing kind
