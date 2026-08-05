"""Tool registry: registration/dispatch invariants and the build_registry wiring.

Uses a stub REPL so the formal tools register and dispatch without a Lean env.
"""
import pytest
from konigsberg_harness.lean_repl import GoalState
from konigsberg_harness.ledger import TrustRoot
from konigsberg_harness.tools.registry import ToolRegistry, build_registry


class StubREPL:
    def __init__(self, gs: GoalState):
        self._gs = gs

    def send(self, snippet, *, timeout_s=None, new_env=False) -> GoalState:
        return self._gs


# --- ToolRegistry basics --------------------------------------------------

def test_register_and_dispatch():
    reg = ToolRegistry()
    reg.register("double", lambda x: x * 2, "doc")
    assert reg.dispatch("double", x=21) == 42


def test_duplicate_registration_rejected():
    reg = ToolRegistry()
    reg.register("t", lambda: None)
    with pytest.raises(ValueError):
        reg.register("t", lambda: None)


def test_dispatch_unknown_raises():
    with pytest.raises(KeyError):
        ToolRegistry().dispatch("nope")


def test_spec_is_serializable_name_doc():
    reg = ToolRegistry()
    reg.register("t", lambda: None, "what it does")
    assert reg.spec() == [{"name": "t", "doc": "what it does"}]


# --- build_registry -------------------------------------------------------

def test_lean_free_registry_has_only_empirical_tools():
    reg = build_registry()
    assert set(reg.names()) == {
        "counterexample_search",
        "choosability_refute",
        "alon_tarsi",
        "fixer_breaker",
    }


def test_registry_with_repl_adds_formal_tools():
    reg = build_registry(StubREPL(GoalState(goals=[], errors=[], infos=[])))
    assert set(reg.names()) == {
        "counterexample_search",
        "choosability_refute",
        "alon_tarsi",
        "fixer_breaker",
        "lean_check",
        "lean_typecheck_statement",
        "lean_search",
        "lean_prove",
    }


def test_dispatch_counterexample_search_mints_claim():
    reg = build_registry()
    claim = reg.dispatch(
        "counterexample_search",
        predicate=lambda g: g.max_degree <= 1,
        bound=3,
    )
    assert claim.provenance.trust_root is TrustRoot.ENUMERATION
    assert "COUNTEREXAMPLE" in claim.statement  # P3 violates max_degree<=1


def test_dispatch_lean_search_routes_through_bound_repl():
    reg = build_registry(StubREPL(GoalState(goals=[], errors=[], infos=["Try this: exact h"])))
    assert reg.dispatch("lean_search", goal="p -> p") == ["exact h"]
