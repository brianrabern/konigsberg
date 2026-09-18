#!/usr/bin/env python3
"""discharging_self_test — prove the discharging engine is not a rubber stamp.

Plants arguments with known answers (v1, D=9):
  1. Closes (must UNAVOIDABLE + mint Claim with closure tag)
  2. Survives (must MISS silently, no Claim, surviving neighborhood returned)
  3. Non-conserving rules (must reject, not MISS)
  4. Ledger coupling (must refuse a core not minted reducible)

Usage:  python ci/discharging_self_test.py
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

from konigsberg_empirical.discharging import CLOSURE_TAG
from konigsberg_empirical.fundamentals.codec import graph6_encode
from konigsberg_harness.campaign import CampaignBind
from konigsberg_harness.ledger import Claim, Ledger, mint_enumeration
from konigsberg_harness.tools.empirical_tools import (
    DischargingResult,
    discharging_unavoidable,
)


def _edge() -> str:
    return graph6_encode(2, [(0, 1)])


def _triangle() -> str:
    return graph6_encode(3, [(0, 1), (0, 2), (1, 2)])


def _plant_forbidden(ledger: Ledger, core: str) -> None:
    ledger.record(
        mint_enumeration(
            f"FORBIDDEN CONFIGURATION (BK minimal counterexample, H_BK): "
            f"core={core}, degree spec d_G=[…]; core is f-choosable.",
            bound="palette<=4",
            exhaustive=True,
            tool="reducible_configuration",
        )
    )


def _run(ledger: Ledger | None, **kwargs):
    bind = CampaignBind()
    bind.ledger = ledger
    return discharging_unavoidable(bind, **kwargs)


def test_closes_unavoidable() -> None:
    core = _edge()
    ledger = Ledger()
    _plant_forbidden(ledger, core)
    result = _run(
        ledger,
        D=9,
        mu={"8": -1, "9": -1},
        rules=[],
        forbidden=[core],
    )
    assert isinstance(result, Claim), f"expected UNAVOIDABLE Claim, got {result!r}"
    stmt = result.statement
    assert "UNAVOIDABLE" in stmt, "HIT Claim missing UNAVOIDABLE"
    assert CLOSURE_TAG in stmt, "HIT Claim missing closure lemma tag"
    assert "avoidable" not in stmt.lower().replace("unavoidable", ""), (
        "HIT Claim must not mention 'avoidable'"
    )
    print("  OK closes → UNAVOIDABLE + closure tag")


def test_survives_miss_silent() -> None:
    core = _triangle()
    ledger = Ledger()
    _plant_forbidden(ledger, core)
    result = _run(
        ledger,
        D=9,
        mu={"8": -1, "9": -1},
        rules=[],
        forbidden=[core],
    )
    assert not isinstance(result, Claim), "MISS must not mint a Claim"
    assert isinstance(result, DischargingResult), (
        f"expected DischargingResult, got {type(result)}"
    )
    text = str(result).lower()
    assert "avoidable" not in text, "MISS must never claim 'avoidable'"
    assert "inconclusive" in text, "MISS should read as inconclusive"
    assert result.survivors, "MISS must return surviving neighborhood types"
    print("  OK survives → MISS silent + survivors")


def test_non_conserving_rejects() -> None:
    core = _edge()
    ledger = Ledger()
    _plant_forbidden(ledger, core)
    try:
        _run(
            ledger,
            D=9,
            mu={"8": -1, "9": -1},
            rules=[{"from_deg": 9, "to_pattern": "self", "amount": 1}],
            forbidden=[core],
        )
    except ValueError as e:
        if "non-conserving" not in str(e).lower():
            raise AssertionError(f"expected non-conserving rejection, got {e}") from e
        print("  OK non-conserving rules rejected")
        return
    raise AssertionError("non-conserving rules must reject, not return a result")


def test_ledger_coupling() -> None:
    core = _edge()
    try:
        result = _run(
            None,
            D=9,
            mu={"8": -1, "9": -1},
            rules=[],
            forbidden=[core],
        )
    except ValueError as e:
        if "ledger coupling" not in str(e).lower():
            raise AssertionError(f"expected ledger coupling refusal, got {e}") from e
        print("  OK ledger coupling refuses unminted core")
        return
    raise AssertionError(
        f"unminted core must be refused, not returned as {result!r}"
    )


def main() -> int:
    print("discharging_self_test:")
    test_closes_unavoidable()
    test_survives_miss_silent()
    test_non_conserving_rejects()
    test_ledger_coupling()
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
