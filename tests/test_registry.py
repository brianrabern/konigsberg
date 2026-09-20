"""Tool registry: registration/dispatch invariants and the build_registry wiring.

Uses a stub REPL so the formal tools register and dispatch without a Lean env.
"""
import pytest
from konigsberg_harness.lean_repl import GoalState
from konigsberg_harness.ledger import TrustRoot
from konigsberg_harness.tools.fundamentals_tools import FUNDAMENTAL_TOOL_NAMES
from konigsberg_harness.tools.registry import ToolRegistry, build_registry


class StubREPL:
    def __init__(self, gs: GoalState):
        self._gs = gs

    def ensure_preamble(self, preamble=None, *, timeout_s=None) -> None:
        return None

    def send(self, snippet, *, timeout_s=None, new_env=False, commit=True) -> GoalState:
        return self._gs


# --- ToolRegistry basics --------------------------------------------------

def test_register_and_dispatch():
    reg = ToolRegistry()
    reg.register("double", lambda x: x * 2, "doc")
    assert reg.dispatch("double", {"x": 21}) == 42
    assert reg.dispatch("double", x=21) == 42  # kwargs still ok for code callers


def test_duplicate_registration_rejected():
    reg = ToolRegistry()
    reg.register("t", lambda: None)
    with pytest.raises(ValueError):
        reg.register("t", lambda: None)


def test_dispatch_unknown_raises():
    with pytest.raises(KeyError):
        ToolRegistry().dispatch("nope", {})


def test_spec_is_serializable_name_doc():
    reg = ToolRegistry()
    reg.register("t", lambda: None, "what it does")
    assert reg.spec() == [{"name": "t", "doc": "what it does"}]


def test_tool_specs_omit_code_only_tools_and_include_schema():
    reg = build_registry()
    specs = {s["name"]: s for s in reg.tool_specs()}
    assert "counterexample_search" not in specs  # code-only, no args_model
    assert "choosability_refute" in specs
    assert "make_graph" in specs
    assert "describe_graph" in specs
    schema = specs["choosability_refute"]["input_schema"]
    props = schema.get("properties", {})
    assert "graph6" in props
    assert "k" in props
    assert "palette" in props
    assert specs["alon_tarsi"]["input_schema"]["properties"].keys() >= {"graph6"}
    assert specs["fixer_breaker"]["input_schema"]["properties"].keys() >= {
        "graph6",
        "list_sizes",
    }
    assert specs["decide_colorable"]["input_schema"]["properties"].keys() >= {
        "graph6",
        "k",
    }
    assert specs["max_degree"]["input_schema"]["properties"].keys() >= {"graph6"}
    assert specs["clique_number"]["input_schema"]["properties"].keys() >= {"graph6"}
    assert specs["chromatic_number"]["input_schema"]["properties"].keys() >= {"graph6"}
    assert specs["bk_predicate"]["input_schema"]["properties"].keys() >= {"graph6"}
    assert specs["bk_search"]["input_schema"]["properties"].keys() >= {
        "n_max",
        "k",
        "n_min",
        "palette",
        "max_hits",
    }
    assert specs["literature_search"]["input_schema"]["properties"].keys() >= {
        "query",
        "area",
        "status",
    }
    assert specs["arxiv_search"]["input_schema"]["properties"].keys() >= {
        "query",
        "max_results",
        "sort_by",
        "category",
    }
    assert specs["list_critical"]["input_schema"]["properties"].keys() >= {
        "graph6",
        "m",
        "palette",
    }
    assert specs["reducible_configuration"]["input_schema"]["properties"].keys() >= {
        "core",
        "degrees",
        "D",
    }
    assert specs["discharging_unavoidable"]["input_schema"]["properties"].keys() >= {
        "D",
        "mu",
        "rules",
        "forbidden",
    }
    assert specs["discharging_cover"]["input_schema"]["properties"].keys() >= {
        "center_deg",
        "n_high",
    }
    assert specs["discharging_search"]["input_schema"]["properties"].keys() >= {
        "D",
        "mu",
        "rules",
        "max_iters",
    }
    assert specs["campaign_status"]["input_schema"]["properties"] == {}
    assert specs["make_graph"]["input_schema"]["properties"].keys() >= {"kind"}


def test_tool_specs_with_repl_include_verify_coloring():
    reg = build_registry(StubREPL(GoalState(goals=[], errors=[], infos=[])))
    specs = {s["name"]: s for s in reg.tool_specs()}
    assert "verify_coloring" in specs
    assert specs["verify_coloring"]["input_schema"]["properties"].keys() >= {
        "graph6",
        "coloring",
    }
    for name in ("lean_check", "lean_typecheck_statement", "lean_search", "lean_prove"):
        assert name in specs


# --- build_registry -------------------------------------------------------

_CORE_EMPIRICAL = {
    "literature_search",
    "arxiv_search",
    "counterexample_search",
    "choosability_refute",
    "alon_tarsi",
    "fixer_breaker",
    "decide_colorable",
    "max_degree",
    "clique_number",
    "chromatic_number",
    "bk_predicate",
    "bk_search",
    "reed_predicate",
    "reed_sweep",
    "list_critical",
    "reducible_configuration",
    "discharging_unavoidable",
    "discharging_cover",
    "discharging_search",
    "campaign_status",
} | set(FUNDAMENTAL_TOOL_NAMES)


def test_lean_free_registry_has_only_empirical_tools():
    reg = build_registry()
    assert set(reg.names()) == _CORE_EMPIRICAL


def test_registry_with_repl_adds_formal_tools():
    reg = build_registry(StubREPL(GoalState(goals=[], errors=[], infos=[])))
    assert set(reg.names()) == _CORE_EMPIRICAL | {
        "lean_check",
        "lean_typecheck_statement",
        "lean_search",
        "lean_prove",
        "lean_add_to_library",
        "lemma_list",
        "lemma_read",
        "verify_coloring",
        "reset_env",
        "retract",
    }


def test_dispatch_counterexample_search_mints_claim():
    reg = build_registry()
    claim = reg.dispatch(
        "counterexample_search",
        {"predicate": (lambda g: g.max_degree <= 1), "bound": 3},
    )
    assert claim.provenance.trust_root is TrustRoot.ENUMERATION
    assert "COUNTEREXAMPLE" in claim.statement  # P3 violates max_degree<=1


def test_dispatch_lean_search_routes_through_bound_repl():
    reg = build_registry(StubREPL(GoalState(goals=[], errors=[], infos=["Try this: exact h"])))
    assert reg.dispatch("lean_search", {"goal": "p -> p"}) == ["exact h"]


def test_dispatch_validates_args_model():
    from pydantic import ValidationError

    reg = build_registry()
    with pytest.raises(ValidationError):
        reg.dispatch("alon_tarsi", {"graph6": 123})  # wrong type
