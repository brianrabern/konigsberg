#!/usr/bin/env python3
"""referee_self_test — prove the referee is not a rubber stamp.

Plants known-flawed claims and asserts the heuristic referee REJECTS each
(Major issue). Also plants one clean claim that must pass heuristic checks.
Uses a stub adversarial model to verify full ``accept`` on the clean claim.

Usage:  python ci/referee_self_test.py
Exit:   0 pass, 1 self-test failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "harness") not in sys.path:
    sys.path.insert(0, str(_ROOT / "harness"))
if str(_ROOT / "empirical") not in sys.path:
    sys.path.insert(0, str(_ROOT / "empirical"))

from konigsberg_harness.models import AssistantText, Tier
from konigsberg_harness.referee import (
    PLANT_CLEAN,
    PLANT_FALSE_CONCLUSION,
    PLANT_SPRODF,
    PLANT_UNCORRECTED_MAIN,
    PLANT_VACUOUS,
    CheckKind,
    run_referee,
    run_tool_grounded_checks,
)
from konigsberg_harness.tools.registry import build_registry


class _AcceptStubModel:
    """Minimal adversarial stub that returns accept JSON."""

    system_prompt = ""

    def respond(self, history, tools, *, tier: Tier):
        return AssistantText(
            '{"recommendation":"accept","established":["adversarial pass clean"],'
            '"major_issues":[],"minor_issues":[],"suggested_revision":"",'
            '"checks":[]}'
        )


def _assert_rejected(label: str, statement: str, *, kind: str | None = None) -> None:
    checks = run_tool_grounded_checks(statement, registry=build_registry())
    report = run_referee(statement, registry=build_registry())
    if report.allows_promotion():
        raise AssertionError(f"{label}: referee accepted a known-flawed claim")
    if (
        report.recommendation not in ("major", "reject", "minor")
        and not report.major_issues
    ):
        raise AssertionError(
            f"{label}: expected Major issues, got {report.recommendation!r}"
        )
    fails = [c for c in checks if c.verdict == "fail"]
    if not fails and not report.major_issues:
        raise AssertionError(f"{label}: no failing checks and no major_issues")
    if kind is not None:
        matching = [c for c in checks if c.kind == kind and c.verdict == "fail"]
        if not matching:
            raise AssertionError(
                f"{label}: expected {kind} to fail, got "
                + ", ".join(f"{c.kind}={c.verdict}" for c in checks)
            )
    print(f"  OK reject {label}")


def _assert_clean_heuristic(label: str, statement: str) -> None:
    checks = run_tool_grounded_checks(statement, registry=build_registry())
    fails = [c for c in checks if c.verdict == "fail"]
    if fails:
        raise AssertionError(
            f"{label}: heuristic checks failed: "
            + "; ".join(f"{c.kind}: {c.detail}" for c in fails)
        )
    report = run_referee(statement, registry=build_registry())
    if report.recommendation == "major" or report.major_issues:
        raise AssertionError(f"{label}: heuristic report has majors: {report.major_issues}")
    if report.allows_promotion():
        raise AssertionError(
            f"{label}: heuristic-only must not allow promotion (fail-closed)"
        )
    if report.recommendation != "no-automated-issues":
        raise AssertionError(
            f"{label}: expected no-automated-issues, got {report.recommendation!r}"
        )
    print(f"  OK clean heuristic {label}")


def _assert_clean_adversarial(label: str, statement: str) -> None:
    report = run_referee(
        statement,
        registry=build_registry(),
        model=_AcceptStubModel(),
    )
    if not report.adversarial_review_ran:
        raise AssertionError(f"{label}: adversarial pass did not run")
    if not report.allows_promotion():
        raise AssertionError(
            f"{label}: clean claim must accept after adversarial pass "
            f"(rec={report.recommendation!r}, majors={report.major_issues})"
        )
    print(f"  OK clean adversarial {label}")


def _assert_unavailable_blocks() -> None:
    class _BrokenModel:
        system_prompt = ""

        def respond(self, history, tools, *, tier: Tier):
            raise RuntimeError("temperature is deprecated for this model")

    report = run_referee(
        PLANT_CLEAN,
        registry=build_registry(),
        model=_BrokenModel(),
    )
    if report.allows_promotion():
        raise AssertionError("unavailable referee must not allow promotion")
    if report.recommendation != "unavailable":
        raise AssertionError(
            f"expected unavailable, got {report.recommendation!r}"
        )
    print("  OK unavailable blocks promotion")


def main() -> int:
    print("referee_self_test: planted flaws must be rejected")
    _assert_rejected(
        "uncorrected main",
        PLANT_UNCORRECTED_MAIN,
        kind=CheckKind.EMPIRICAL_CROSS_CHECK.value,
    )
    _assert_rejected(
        "sProdF/lProdF unbridged",
        PLANT_SPRODF,
        kind=CheckKind.DEFINITION_FAITHFULNESS.value,
    )
    _assert_rejected(
        "vacuous hypothesis",
        PLANT_VACUOUS,
        kind=CheckKind.VACUITY_TRIVIALITY.value,
    )
    _assert_rejected(
        "⇒ False without sat witness",
        PLANT_FALSE_CONCLUSION,
        kind=CheckKind.VACUITY_TRIVIALITY.value,
    )
    faith = [
        c
        for c in run_tool_grounded_checks(
            PLANT_FALSE_CONCLUSION, registry=build_registry()
        )
        if c.kind == CheckKind.DEFINITION_FAITHFULNESS.value
    ]
    if not faith or faith[0].verdict == "na":
        raise AssertionError(
            "⇒ False plant: faithfulness must see KCritical/FChoosableZ, not na"
        )
    print("  OK faithfulness sees corpus names on ⇒ False plant")
    _assert_rejected(
        "missing hypothesis (unqualified hitting)",
        PLANT_UNCORRECTED_MAIN,
        kind=CheckKind.HYPOTHESIS_NECESSITY.value,
    )
    _assert_clean_heuristic("corrected triangle-free", PLANT_CLEAN)
    _assert_clean_adversarial("corrected triangle-free", PLANT_CLEAN)
    _assert_unavailable_blocks()
    print("referee_self_test: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
