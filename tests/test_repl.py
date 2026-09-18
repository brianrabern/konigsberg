"""Slash-command smoke tests with a fake model (no network)."""
from __future__ import annotations

from konigsberg_harness.lean_repl import GoalState
from konigsberg_harness.models import AssistantText
from konigsberg_harness.repl import Repl, ScriptedReplModel, formal_tier_label
from konigsberg_harness.session import SessionStore
from konigsberg_harness.tools.fundamentals_tools import FUNDAMENTAL_TOOL_NAMES
from konigsberg_harness.tools.registry import ToolRegistry, build_registry
from pydantic import BaseModel


class StubREPL:
    def __init__(self, gs: GoalState):
        self._gs = gs

    def send(self, snippet, *, timeout_s=None, new_env=False, commit=True) -> GoalState:
        return self._gs


class _NoteArgs(BaseModel):
    text: str


_EMPIRICAL = {
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
    "campaign_status",
} | set(FUNDAMENTAL_TOOL_NAMES)

_FORMAL = {
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

_ALL_TOOLS = _EMPIRICAL | _FORMAL

_MODEL_EXPOSED_WITH_LEAN = _ALL_TOOLS - {"counterexample_search"}


def test_build_registry_stub_repl_exposes_all_tools_via_repl_tool_specs(capsys, tmp_path):
    """build_registry(stub_repl) → all tools; model-exposed omit code-only."""
    stub = StubREPL(GoalState(goals=[], errors=[], infos=[]))
    reg = build_registry(stub)
    assert set(reg.names()) == _ALL_TOOLS

    store = SessionStore(tmp_path)
    repl = Repl(store=store, registry=reg, model=ScriptedReplModel(), lean_repl=None)
    assert formal_tier_label(repl.registry) == "formal tier: live"
    assert repl.handle_slash("/tools") is False
    out = capsys.readouterr().out
    assert "formal tier: live" in out
    specs = {s["name"] for s in repl.registry.tool_specs()}
    assert specs == _MODEL_EXPOSED_WITH_LEAN
    for name in _MODEL_EXPOSED_WITH_LEAN:
        assert name in out


def test_tools_header_unavailable_when_lean_free(capsys, tmp_path):
    store = SessionStore(tmp_path)
    reg = build_registry()  # no repl
    repl = Repl(store=store, registry=reg, model=ScriptedReplModel())
    assert formal_tier_label(repl.registry) == (
        "formal tier: unavailable (no Lean toolchain)"
    )
    assert repl.handle_slash("/tools") is False
    out = capsys.readouterr().out
    assert "formal tier: unavailable (no Lean toolchain)" in out
    # Formal tools must not be registered (docstrings of empirical tools may
    # mention verify_coloring as an upgrade path).
    names = {s["name"] for s in repl.registry.tool_specs()}
    assert "verify_coloring" not in names
    assert "lean_prove" not in names
    assert "chromatic_number" in names
    assert "bk_predicate" in names


def test_slash_ledger_tools_compact(tmp_path, capsys):
    store = SessionStore(tmp_path)
    reg = ToolRegistry()
    reg.register("note", lambda text: text, "doc", args_model=_NoteArgs)
    model = ScriptedReplModel([AssistantText("Summary of earlier work: n/a")])
    repl = Repl(store=store, registry=reg, model=model)
    from konigsberg_harness.ledger import mint_conjecture

    repl.session.ledger.record(mint_conjecture("hunch"))

    assert repl.handle_slash("/help") is False
    assert repl.handle_slash("/tools") is False
    assert repl.handle_slash("/ledger") is False
    assert repl.handle_slash("/claim") is False
    out = capsys.readouterr().out
    assert "note" in out
    assert "hunch" in out or "conjectured" in out
    assert "/claim" in out or "claim" in out.lower()
    assert "/hunt" in out
    assert "/forever" in out
    assert "/lemmas" in out
    # Custom registry without formal tools → unavailable header.
    assert "formal tier: unavailable" in out

    from konigsberg_harness.models import UserMsg

    for i in range(15):
        repl.session.history.append(UserMsg(f"pad {i}"))
    from konigsberg_harness.compaction import CompactionConfig

    repl.compaction = CompactionConfig(threshold=1, keep_recent=2)
    assert repl.handle_slash("/compact") is False
    assert any("Summary" in getattr(i, "text", "") for i in repl.session.history)
    assert len(repl.session.ledger.claims()) == 1


def test_claim_slash_renders_verbatim(tmp_path, capsys):
    from konigsberg_harness.ledger import mint_certificate

    store = SessionStore(tmp_path)
    repl = Repl(store=store, registry=ToolRegistry(), model=ScriptedReplModel())
    repl.session.ledger.record(
        mint_certificate(
            "C~ IS 4-list-critical (Bad 3-list [[0, 1, 2], [0, 1, 2], [0, 1, 2], [0, 1, 2]])",
            checker="choosability.verify_bad_list",
            tool="list_critical",
        )
    )
    assert repl.handle_slash("/claim") is False
    out = capsys.readouterr().out
    assert "Bad 3-list" in out
    assert "[0, 1, 2]" in out
    assert "certificate-checked" in out
    assert "C~ IS 4-list-critical" in out.replace("\n", " ")


def test_show_the_certificate_intercept_skips_model(tmp_path, capsys):
    from konigsberg_harness.ledger import mint_certificate

    store = SessionStore(tmp_path)
    model = ScriptedReplModel([AssistantText("should not run")])
    repl = Repl(store=store, registry=ToolRegistry(), model=model)
    repl.session.ledger.record(
        mint_certificate("stored-cert-xyz", checker="c", tool="t")
    )
    assert repl._try_claim_display("Show the certificate") is True
    out = capsys.readouterr().out
    assert "stored-cert-xyz" in out
    assert model._q  # model queue untouched
