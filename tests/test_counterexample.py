"""Counterexample search: the highest-ROI empirical tool.

Covers the search primitive (first_violation / validate_predicate) and the
harness tool that wraps it into a provenance-stamped ledger Claim.
"""
from konigsberg_empirical.core import Graph
from konigsberg_empirical.search.counterexample import first_violation, validate_predicate


def _has_max_degree_le_1(g: Graph) -> bool:
    return g.max_degree <= 1


# --- validate_predicate ---------------------------------------------------

def test_validate_predicate_matches_known_cases():
    empty2 = Graph.of(2, [])
    edge2 = Graph.of(2, [(0, 1)])
    cases = [(empty2, True), (edge2, True)]
    assert validate_predicate(_has_max_degree_le_1, cases) is True


def test_validate_predicate_flags_mismatch():
    triangle = Graph.of(3, [(0, 1), (1, 2), (0, 2)])
    assert validate_predicate(_has_max_degree_le_1, [(triangle, True)]) is False


# --- first_violation ------------------------------------------------------

def test_first_violation_finds_a_counterexample():
    # P3 (a path on 3 vertices) has a degree-2 vertex: violates max_degree<=1.
    witness = first_violation(_has_max_degree_le_1, bound=3)
    assert witness is not None
    assert witness.max_degree >= 2


def test_first_violation_returns_none_when_predicate_always_holds():
    assert first_violation(lambda g: True, bound=4) is None


# --- harness tool: provenance-stamped Claim -------------------------------

def test_counterexample_search_tool_mints_enumeration_claims():
    from konigsberg_harness.ledger import EvidenceKind, TrustRoot
    from konigsberg_harness.tools.empirical_tools import counterexample_search

    hit = counterexample_search(_has_max_degree_le_1, bound=3)
    assert hit is not None
    assert hit.provenance.trust_root is TrustRoot.ENUMERATION
    assert hit.provenance.label() == "python-checked"
    assert "COUNTEREXAMPLE" in hit.statement

    clean = counterexample_search(lambda g: True, bound=3)
    assert clean.provenance.trust_root is TrustRoot.ENUMERATION
    assert clean.provenance.evidence_kind is EvidenceKind.EXHAUSTIVE
    assert "COUNTEREXAMPLE" not in clean.statement
