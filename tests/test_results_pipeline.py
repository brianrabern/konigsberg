"""Referee gate + lean_add_to_library write-back (results pipeline)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from konigsberg_harness.ledger import mint_lean_proof
from konigsberg_harness.models import AssistantText, Tier, ToolCall
from konigsberg_harness.referee import (
    PLANT_CLEAN,
    PLANT_FALSE_CONCLUSION,
    PLANT_SPRODF,
    PLANT_UNCORRECTED_MAIN,
    PLANT_VACUOUS,
    REFEREE_PROMPT,
    CheckKind,
    RefereeReport,
    check_definition_faithfulness,
    check_empirical_cross_check,
    check_vacuity_triviality,
    parse_referee_report,
    run_referee,
    run_tool_grounded_checks,
)
from konigsberg_harness.tools.library_writeback import (
    LibraryWriteError,
    lean_add_to_library,
)
from konigsberg_harness.tools.registry import build_registry


class _AcceptStubModel:
    system_prompt = ""

    def respond(self, history, tools, *, tier: Tier):
        return AssistantText(
            '{"recommendation":"accept","established":[],"major_issues":[],'
            '"minor_issues":[],"suggested_revision":"","checks":[]}'
        )


def test_referee_prompt_break_it_fairly():
    assert "break-it-fairly" in REFEREE_PROMPT.lower()
    assert "kernel checks the proof" in REFEREE_PROMPT
    assert "lean_add_to_library" in REFEREE_PROMPT


def test_uncorrected_main_empirical_cross_check_fails():
    finding = check_empirical_cross_check(PLANT_UNCORRECTED_MAIN)
    assert finding.verdict == "fail"
    assert "K₃" in finding.detail or "non-bipartite" in finding.detail


def test_sprodf_definition_faithfulness_fails():
    finding = check_definition_faithfulness(PLANT_SPRODF)
    assert finding.verdict == "fail"
    assert "sProdF" in finding.detail or "lProdF" in finding.detail


def test_fchoosable_ident_is_not_unbridged_choosability_claim():
    """Corpus names like FChoosableZ must not trip the 'choosability' standard-notion fail."""
    finding = check_definition_faithfulness(
        "Konigsberg.Literature.Coloring.BK_ReducibleOfFChoosable.reducible_of_fChoosable",
        lean_type=(
            "reducible_of_fChoosable (G : SimpleGraph V) (h : KCritical G 9) : "
            "FChoosableZ G f → False"
        ),
    )
    assert finding.verdict != "fail"


def test_bespoke_extract_does_not_slice_pascal_interiors():
    from konigsberg_harness.referee import _extract_bespoke_definitions

    names = _extract_bespoke_definitions(
        "Konigsberg.Literature.Coloring.CompleteGraphKCritical."
        "completeGraph_kCritical  SanityChecks  KCritical"
    )
    assert "ompleteGraphKCritical" not in names
    assert "anityChecks" not in names
    assert "kCritical" not in names
    assert "CompleteGraphKCritical" in names
    assert "SanityChecks" in names
    assert "KCritical" in names


def test_vacuous_claim_fails():
    checks = run_tool_grounded_checks(PLANT_VACUOUS, registry=build_registry())
    vac = next(c for c in checks if c.kind == CheckKind.VACUITY_TRIVIALITY.value)
    assert vac.verdict == "fail"


def test_false_conclusion_without_witness_fails():
    finding = check_vacuity_triviality(PLANT_FALSE_CONCLUSION)
    assert finding.verdict == "fail"
    assert "False" in finding.detail
    checks = run_tool_grounded_checks(
        PLANT_FALSE_CONCLUSION, registry=build_registry()
    )
    vac = next(c for c in checks if c.kind == CheckKind.VACUITY_TRIVIALITY.value)
    assert vac.verdict == "fail"
    faith = next(
        c for c in checks if c.kind == CheckKind.DEFINITION_FAITHFULNESS.value
    )
    assert faith.verdict != "na"
    hyp = next(c for c in checks if c.kind == CheckKind.HYPOTHESIS_NECESSITY.value)
    assert hyp.verdict != "na"


def test_false_conclusion_with_sanitychecks_witness_passes_vacuity():
    stmt = PLANT_FALSE_CONCLUSION + " SanityChecks: inhabited instance of KCritical."
    assert check_vacuity_triviality(stmt).verdict == "pass"


def test_false_conclusion_witness_in_lean_type_notes_passes_vacuity():
    assert (
        check_vacuity_triviality(
            "Konigsberg.Literature.Coloring.BK_ReducibleOfFChoosable.reducible_of_fChoosable",
            lean_type="KCritical G D → FChoosableZ G f → False",
            notes="SanityChecks: K_k is k-critical (completeGraph_kCritical).",
        ).verdict
        == "pass"
    )


def test_vacuity_and_faithfulness_read_lean_type_not_claim_string():
    from konigsberg_harness.lean_repl import GoalState

    lean_type = (
        "reducible_of_fChoosable (G : SimpleGraph V) (h : KCritical G 9) : "
        "FChoosableZ G f → False"
    )

    class _Repl:
        def send(self, snippet, *, commit=False, timeout_s=None, new_env=False):
            return GoalState(goals=[], errors=[], infos=[lean_type])

        def print_axioms(self, _name, **_kwargs):
            return ["propext"]

    checks = run_tool_grounded_checks(
        "reducible_of_fChoosable",
        registry=build_registry(),
        repl=_Repl(),
        lean_name="reducible_of_fChoosable",
    )
    vac = next(c for c in checks if c.kind == CheckKind.VACUITY_TRIVIALITY.value)
    assert vac.verdict == "fail"
    faith = next(
        c for c in checks if c.kind == CheckKind.DEFINITION_FAITHFULNESS.value
    )
    assert faith.verdict != "na"
    assert "KCritical" in faith.detail or "FChoosableZ" in faith.detail


_ACCEPT_JSON = (
    '{"recommendation":"accept","established":["forced"],"major_issues":[],'
    '"minor_issues":[],"suggested_revision":"","checks":[]}'
)


class _ToolThenJson:
    """Tool-only until cap, then JSON on the no-tools force turn."""

    system_prompt = ""

    def respond(self, history, tools, *, tier: Tier):
        if not tools:
            return AssistantText(_ACCEPT_JSON)
        return [
            ToolCall(
                id="1",
                name="literature_search",
                args={"query": "BK"},
            )
        ]


class _ToolThenEmpty:
    system_prompt = ""

    def respond(self, history, tools, *, tier: Tier):
        if not tools:
            return AssistantText("")
        return [
            ToolCall(
                id="1",
                name="literature_search",
                args={"query": "BK"},
            )
        ]


def test_referee_force_json_after_step_exhaustion():
    report = run_referee(
        PLANT_CLEAN,
        registry=build_registry(),
        model=_ToolThenJson(),
        max_steps=1,
    )
    assert report.adversarial_review_ran
    assert report.allows_promotion()


def test_referee_exhaustion_without_json_is_unavailable():
    report = run_referee(
        PLANT_CLEAN,
        registry=build_registry(),
        model=_ToolThenEmpty(),
        max_steps=1,
    )
    assert report.recommendation == "unavailable"
    assert not report.allows_promotion()
    assert "exhausted steps" in report.review_unavailable_reason
    assert "model error" not in report.review_unavailable_reason


def test_referee_rejects_uncorrected_main_heuristic():
    report = run_referee(PLANT_UNCORRECTED_MAIN, registry=build_registry())
    assert not report.allows_promotion()
    assert report.recommendation in ("major", "reject", "minor")
    assert report.major_issues


def test_referee_heuristic_only_is_not_accept():
    """Fail-closed: no model → no-automated-issues, not accept."""
    report = run_referee(PLANT_CLEAN, registry=build_registry())
    assert report.recommendation == "no-automated-issues"
    assert not report.allows_promotion()
    assert not report.adversarial_review_ran


def test_referee_accepts_clean_with_adversarial_stub():
    report = run_referee(
        PLANT_CLEAN,
        registry=build_registry(),
        model=_AcceptStubModel(),
    )
    assert report.adversarial_review_ran
    assert report.allows_promotion()
    assert report.recommendation == "accept"


def test_referee_unavailable_on_model_error():
    class _Broken:
        system_prompt = ""

        def respond(self, history, tools, *, tier: Tier):
            raise RuntimeError("temperature is deprecated for this model")

    report = run_referee(
        PLANT_CLEAN,
        registry=build_registry(),
        model=_Broken(),
    )
    assert report.recommendation == "unavailable"
    assert not report.allows_promotion()
    assert report.review_unavailable_reason.startswith("model error")
    assert "temperature" in report.review_unavailable_reason.lower()


def test_parse_referee_report_sets_adversarial_ran():
    raw = (
        '{"recommendation":"accept","established":["ok"],"major_issues":[],'
        '"minor_issues":[],"suggested_revision":"","checks":[]}'
    )
    r = parse_referee_report(raw)
    assert r.adversarial_review_ran
    assert r.allows_promotion()


def test_accept_keeps_nonblocking_minor_notes():
    """Caveats (folklore, already-disclosed naming) must not block promotion."""

    class _AcceptWithCaveat:
        system_prompt = ""

        def respond(self, history, tools, *, tier: Tier):
            return AssistantText(
                '{"recommendation":"accept","established":["kernel-clean"],'
                '"major_issues":[],'
                '"minor_issues":["folklore infrastructure, not novel"],'
                '"suggested_revision":"","checks":[]}'
            )

    report = run_referee(
        PLANT_CLEAN,
        registry=build_registry(),
        model=_AcceptWithCaveat(),
    )
    assert report.recommendation == "accept"
    assert report.minor_issues
    assert report.allows_promotion()


def test_lean_add_to_library_refuses_without_accept(tmp_path):
    repl = MagicMock()
    repl.ensure_preamble = MagicMock()
    bad = RefereeReport(recommendation="major", major_issues=("proxy≠property",))
    with pytest.raises(LibraryWriteError, match="referee did not accept"):
        lean_add_to_library(
            repl,
            "Konigsberg.Literature.Coloring.HittingCliqueBlowup.main",
            "theorem main : True := trivial",
            area="coloring",
            citation="test",
            informal_statement=PLANT_UNCORRECTED_MAIN,
            referee_report=bad,
            confirmed=True,
            formal_root=tmp_path,
        )


def test_lean_add_to_library_refuses_no_automated_issues(tmp_path):
    repl = MagicMock()
    heuristic = RefereeReport(recommendation="no-automated-issues")
    with pytest.raises(LibraryWriteError, match="heuristic-only"):
        lean_add_to_library(
            repl,
            "Konigsberg.Literature.Coloring.X.main",
            "theorem main : True := trivial",
            area="coloring",
            citation="test",
            informal_statement=PLANT_CLEAN,
            referee_report=heuristic,
            confirmed=True,
            formal_root=tmp_path,
        )


def test_lean_add_to_library_refuses_unavailable(tmp_path):
    repl = MagicMock()
    unavail = RefereeReport(
        recommendation="unavailable",
        review_unavailable_reason="model error",
    )
    with pytest.raises(LibraryWriteError, match="REFEREE UNAVAILABLE"):
        lean_add_to_library(
            repl,
            "Konigsberg.Literature.Coloring.X.main",
            "theorem main : True := trivial",
            area="coloring",
            citation="test",
            informal_statement=PLANT_CLEAN,
            referee_report=unavail,
            confirmed=True,
            formal_root=tmp_path,
        )


def test_lean_add_to_library_refuses_without_confirm(tmp_path):
    repl = MagicMock()
    good = RefereeReport(recommendation="accept", adversarial_review_ran=True)
    with pytest.raises(LibraryWriteError, match="human confirmation"):
        lean_add_to_library(
            repl,
            "Konigsberg.Literature.Coloring.HittingCliqueBlowup.main",
            "theorem main : True := trivial",
            area="coloring",
            citation="test",
            informal_statement=PLANT_CLEAN,
            referee_report=good,
            confirmed=False,
            formal_root=tmp_path,
        )


def test_lean_add_to_library_refuses_non_durable(tmp_path):
    repl = MagicMock()
    session_only = mint_lean_proof("True", axioms=(), tool="lean_prove", durable=False)
    good = RefereeReport(recommendation="accept", adversarial_review_ran=True)
    with pytest.raises(LibraryWriteError, match="session-only"):
        lean_add_to_library(
            repl,
            "Konigsberg.Literature.Coloring.X.main",
            "theorem main : True := trivial",
            area="coloring",
            citation="test",
            informal_statement=PLANT_CLEAN,
            referee_report=good,
            confirmed=True,
            formal_root=tmp_path,
            source_claim=session_only,
        )


def test_lean_add_to_library_promotes_with_adversarial_accept(tmp_path):
    formal = tmp_path / "formal"
    lit_barrel = formal / "Konigsberg" / "Literature.lean"
    lit_barrel.parent.mkdir(parents=True)
    lit_barrel.write_text("-/\n", encoding="utf-8")

    class _GS:
        ok = True
        errors = ()  # type: ignore[var-annotated]
        env = 1

    repl = MagicMock()
    repl.snapshot = MagicMock(return_value=(None, False, ()))
    repl.restore = MagicMock()
    repl.load_preamble = MagicMock(return_value=_GS())
    repl.send_transactional = MagicMock(return_value=_GS())
    repl.send = MagicMock(return_value=_GS())
    repl.print_axioms = MagicMock(
        return_value=["propext", "Classical.choice", "Quot.sound"]
    )

    report = run_referee(
        PLANT_CLEAN,
        registry=build_registry(),
        model=_AcceptStubModel(),
    )
    assert report.allows_promotion()

    lean_name = "Konigsberg.Literature.Coloring.HittingCliqueBlowup.hittingCliqueBlowup"
    snippet = "theorem hittingCliqueBlowup : True := by\n  trivial\n"
    sanity = (
        "import Konigsberg.Literature.Coloring.HittingCliqueBlowup.Statements\n"
        "namespace Konigsberg.Literature.Coloring.HittingCliqueBlowup\n"
        "example : True := trivial\n"
        "end Konigsberg.Literature.Coloring.HittingCliqueBlowup\n"
    )
    source = mint_lean_proof(
        lean_name, axioms=("propext",), tool="lean_prove", durable=True
    )
    claim = lean_add_to_library(
        repl,
        lean_name,
        snippet,
        area="coloring",
        citation="docs/research/HITTING_CLIQUES.md (corrected)",
        informal_statement=PLANT_CLEAN,
        referee_report=report,
        sanity_snippet=sanity,
        confirmed=True,
        formal_root=formal,
        run_gates=True,
        source_claim=source,
    )
    assert claim.provenance.label() == "proved"
    assert claim.provenance.durable is True
    notes = (
        formal
        / "Konigsberg"
        / "Literature"
        / "Coloring"
        / "HittingCliqueBlowup"
        / "Notes.md"
    ).read_text(encoding="utf-8")
    assert "## Referee report" in notes
    assert "Review mode: full adversarial" in notes


def test_na_checks_have_justification():
    checks = run_tool_grounded_checks(
        "Brooks theorem for general graphs.",
        registry=build_registry(),
    )
    nas = [c for c in checks if c.verdict == "na"]
    assert nas
    for c in nas:
        assert c.na_justification or "no " in c.detail.lower()


def test_slash_help_mentions_referee_promote():
    from konigsberg_harness.repl import SLASH_HELP

    assert "/referee" in SLASH_HELP
    assert "/promote" in SLASH_HELP
    assert "/reset" in SLASH_HELP


def test_proved_claim_offer_path_exists():
    from konigsberg_harness.agent import ClaimMinted

    c = mint_lean_proof("True", axioms=(), tool="lean_prove")
    assert ClaimMinted(c).claim.provenance.label() == "proved"
    assert "[session-only]" in c.render()
    d = mint_lean_proof("True", axioms=(), tool="lean_prove", durable=True)
    assert "[durable]" in d.render()
