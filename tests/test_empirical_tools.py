"""Harness empirical tools that mint Claims — focus on the CEGAR choosability
tool and the trust roots it stamps. Skipped when python-sat is absent.
"""
import networkx as nx
import pytest
from konigsberg_empirical.coloring import choosability as ch
from konigsberg_harness.ledger import TrustRoot
from konigsberg_harness.tools.empirical_tools import choosability_refute

pytestmark = pytest.mark.skipif(not ch.is_available(), reason="python-sat not installed")


def g6(G) -> str:
    return nx.to_graph6_bytes(G, header=False).decode().strip()


def test_refute_triangle_k2_is_certificate_checked():
    claim = choosability_refute(g6(nx.complete_graph(3)), 2)
    assert claim.provenance.trust_root is TrustRoot.CERTIFICATE
    assert claim.provenance.label() == "certificate-checked"
    assert "NOT 2-choosable" in claim.statement


def test_refute_triangle_k3_is_complete_python_checked():
    claim = choosability_refute(g6(nx.complete_graph(3)), 3)
    assert claim.provenance.trust_root is TrustRoot.ENUMERATION
    assert claim.provenance.label() == "python-checked"
    assert "3-choosable" in claim.statement


def test_smaller_palette_miss_is_not_a_complete_decision():
    # a null result below the completeness bound is bounded, not decided
    claim = choosability_refute(g6(nx.complete_graph(3)), 3, palette=3)
    assert claim.provenance.evidence_kind.name == "SAMPLED"  # not EXHAUSTIVE
    assert "=> 3-choosable" not in claim.statement
