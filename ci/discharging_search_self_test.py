#!/usr/bin/env python3
"""discharging_search_self_test — toy close vs unclosable residual.

  1. Minted edge + μ={-1,-1} + catalog containing that edge → CLOSED
  2. Empty catalog + μ={0,+1} → STUCK with a non-empty residual
     (irreducible-frontier text, not a forbidden-config / UNAVOIDABLE HIT)

Usage:  python ci/discharging_search_self_test.py
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

from konigsberg_empirical.discharging.catalog import CatalogEntry
from konigsberg_empirical.discharging.search import (
    format_search_banner,
    frontier_statement,
    run_search,
)
from konigsberg_empirical.fundamentals.codec import graph6_encode
from konigsberg_harness.campaign import CampaignBind, has_unavoidable
from konigsberg_harness.ledger import Claim, Ledger, mint_enumeration
from konigsberg_harness.tools.empirical_tools import discharging_search


def _edge() -> str:
    return graph6_encode(2, [(0, 1)])


def _entry(core: str) -> CatalogEntry:
    return CatalogEntry(
        name="toy_edge",
        core=core,
        degrees=(8, 8),
        D=9,
        source="Rabern BK catalog (offline); self-test",
        note="reducers: offline",
        reducers=frozenset({"offline"}),
    )


def _plant(ledger: Ledger, core: str) -> None:
    ledger.record(
        mint_enumeration(
            f"FORBIDDEN CONFIGURATION (BK): core={core}, degree spec d_G=[8,8]",
            bound="palette<=4",
            exhaustive=True,
            tool="reducible_configuration",
        )
    )


def test_toy_closes() -> None:
    edge = _edge()
    outcome = run_search(
        mu={8: -1, 9: -1},
        rules=[],
        forbidden=[],
        reducible_cores={edge},
        catalog=(_entry(edge),),
        max_iters=4,
    )
    assert outcome.status == "CLOSED", outcome
    assert outcome.result.hit
    assert not outcome.result.ranked
    assert edge in outcome.forbidden
    print("  OK toy regime → CLOSED (survivor_count → 0)")


def test_unclosable_stuck() -> None:
    outcome = run_search(
        mu={8: 0, 9: 1},
        rules=[],
        forbidden=[],
        reducible_cores=set(),
        catalog=(),
        max_iters=6,
    )
    assert outcome.status == "STUCK", outcome
    assert outcome.result.ranked, "unclosable regime must leave a residual"
    banner = format_search_banner(outcome)
    assert "DISCHARGING_SEARCH STUCK" in banner
    stmt = frontier_statement(outcome)
    assert "IRREDUCIBLE-FRONTIER" in stmt
    assert "UNAVOIDABLE (BK" not in stmt
    lowered = stmt.lower().replace("unavoidable", "")
    assert "avoidable" not in lowered
    print("  OK unclosable regime → STUCK residual (not a false closure)")


def test_tool_frontier_is_not_forbidden() -> None:
    bind = CampaignBind()
    bind.ledger = Ledger()
    result = discharging_search(
        bind,
        D=9,
        mu={"8": 0, "9": 1},
        rules=[],
        forbidden=[],
        max_iters=4,
    )
    assert isinstance(result, Claim), f"expected frontier Claim, got {result!r}"
    assert "IRREDUCIBLE-FRONTIER" in result.statement
    assert "FORBIDDEN CONFIGURATION" not in result.statement
    assert not has_unavoidable([result])
    print("  OK STUCK mints irreducible-frontier, not forbidden-config")


def main() -> int:
    print("discharging_search_self_test:")
    test_toy_closes()
    test_unclosable_stuck()
    test_tool_frontier_is_not_forbidden()
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
