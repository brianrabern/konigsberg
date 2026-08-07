"""BK invariant tools: Δ, ω, χ certificates + bk_predicate + bk_search."""
from __future__ import annotations

import re

import networkx as nx
import pytest
from konigsberg_empirical.coloring import choosability as ch
from konigsberg_harness.ledger import TrustRoot
from konigsberg_harness.tools.empirical_tools import (
    bk_predicate,
    bk_search,
    chromatic_number,
    clique_number,
    max_degree,
)
from konigsberg_harness.tools.registry import build_registry

needs_sat = pytest.mark.skipif(not ch.is_available(), reason="python-sat not installed")

_K4 = "C~"  # K₄
_STAR10 = "IsaCCA?_?"  # star on 10 vertices, Δ=9


def _g6(G) -> str:
    return nx.to_graph6_bytes(G, header=False).decode().strip()


def test_max_degree_k4():
    claim = max_degree(_K4)
    assert claim.provenance.label() == "python-checked"
    assert "Δ=3" in claim.statement


def test_clique_number_k4():
    claim = clique_number(_K4)
    assert claim.provenance.trust_root is TrustRoot.CERTIFICATE
    assert claim.provenance.label() == "certificate-checked"
    assert "ω=4" in claim.statement
    assert "witnessing clique" in claim.statement


def test_chromatic_number_k4_has_coloring_and_lower_bound():
    claim = chromatic_number(_K4)
    assert "χ=4" in claim.statement
    assert "χ-coloring" in claim.statement
    assert "not 3-colorable" in claim.statement
    assert claim.provenance.trust_root is TrustRoot.CERTIFICATE
    # coloring list present
    assert re.search(r"χ-coloring \[.*?\]", claim.statement)


def test_bk_predicate_rejects_delta_below_9():
    claim = bk_predicate(_K4)
    assert "hypothesis not met" in claim.statement
    assert "Δ=3" in claim.statement
    assert claim.provenance.label() == "python-checked"


def test_bk_predicate_star_satisfies():
    """Star K_{1,9}: Δ=9, ω=2, χ=2 ≤ max(2,8)=8 → satisfies BK."""
    claim = bk_predicate(_STAR10)
    assert "satisfies BK" in claim.statement
    assert "Δ=9" in claim.statement
    assert "χ=2" in claim.statement
    assert claim.provenance.trust_root is TrustRoot.CERTIFICATE
    assert "clique" in claim.statement
    assert "χ-coloring" in claim.statement
    assert "degrees" in claim.statement


def test_invariant_tools_registered_lean_free():
    reg = build_registry()
    for name in (
        "max_degree",
        "clique_number",
        "chromatic_number",
        "bk_predicate",
        "bk_search",
    ):
        assert name in reg.names()
    specs = {s["name"] for s in reg.tool_specs()}
    assert specs >= {
        "max_degree",
        "clique_number",
        "chromatic_number",
        "bk_predicate",
        "bk_search",
    }


@needs_sat
def test_bk_search_documents_family_limits():
    claim = bk_search(n_max=6, n_min=6, k=3, palette=4, max_hits=1)
    assert claim.provenance.tool == "bk_search"
    assert "LIMITS" in claim.statement
    assert "deg∈{3,4}" in claim.statement or "deg∈{{3,4}}" in claim.statement
    assert "Δ≥9" in claim.statement or "not a Δ" in claim.statement


def test_bk_search_bad_range_raises():
    with pytest.raises(ValueError):
        bk_search(n_max=3, n_min=5)
