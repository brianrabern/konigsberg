#!/usr/bin/env python3
"""reduction_self_test — prove the reducible-configuration engine is not a rubber stamp.

Plants configurations with known answers:
  1. Known-reducible (must HIT + mint Claim; bridge tag iff Literature unproved)
  2. Known-not-establishable (must MISS silently, no Claim)
  3. Out-of-scope f(v)≤0 (clean MISS, no crash)

Usage:  python ci/reduction_self_test.py
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

from konigsberg_empirical.coloring import choosability as _ch
from konigsberg_empirical.fundamentals.codec import graph6_encode
from konigsberg_empirical.reduction import BRIDGE_TAG, bridge_is_formalized
from konigsberg_harness.ledger import Claim
from konigsberg_harness.tools.empirical_tools import (
    ReducibleConfigurationResult,
    reducible_configuration,
)


def _require_pysat() -> None:
    if not _ch.is_available():
        print("SKIP: pysat not installed")
        sys.exit(0)


def _path3() -> str:
    return graph6_encode(3, [(0, 1), (1, 2)])


def _cycle4() -> str:
    return graph6_encode(4, [(0, 1), (1, 2), (2, 3), (3, 0)])


def _edge() -> str:
    return graph6_encode(2, [(0, 1)])


def test_known_reducible_hit() -> None:
    core = _path3()
    result = reducible_configuration(core, degrees=[8, 8, 8], D=10)
    assert isinstance(result, Claim), f"expected HIT Claim, got {result!r}"
    if "FORBIDDEN CONFIGURATION" not in result.statement:
        raise AssertionError("HIT Claim missing forbidden-configuration header")
    if "not reducible" in result.statement.lower():
        raise AssertionError("HIT Claim must not mention 'not reducible'")
    if bridge_is_formalized():
        if BRIDGE_TAG in result.statement:
            raise AssertionError(
                "HIT Claim must drop the bridge tag once Literature is formalized"
            )
        print("  OK known-reducible HIT; bridge tag dropped (formalized)")
    else:
        if BRIDGE_TAG not in result.statement:
            raise AssertionError("HIT Claim missing bridge lemma tag")
        print("  OK known-reducible HIT + bridge tag")


def _triangle() -> str:
    return graph6_encode(3, [(0, 1), (0, 2), (1, 2)])


def test_known_miss_silent() -> None:
    core = _triangle()
    result = reducible_configuration(core, degrees=[8, 8, 8], D=9)
    assert not isinstance(result, Claim), "MISS must not mint a Claim"
    assert isinstance(result, ReducibleConfigurationResult), (
        f"expected ReducibleConfigurationResult, got {type(result)}"
    )
    if "not reducible" in str(result).lower():
        raise AssertionError("MISS must never claim 'not reducible'")
    if "inconclusive" not in str(result).lower():
        raise AssertionError("MISS should read as inconclusive")
    print("  OK known MISS silent (no Claim)")


def test_out_of_scope() -> None:
    core = _edge()
    result = reducible_configuration(core, degrees=[9, 9], D=9)
    assert not isinstance(result, Claim), "out-of-scope must not mint a Claim"
    if not isinstance(result, ReducibleConfigurationResult) or not result.out_of_scope:
        raise AssertionError(f"expected out_of_scope result, got {result!r}")
    print("  OK out-of-scope MISS (no crash)")


def main() -> int:
    _require_pysat()
    print("reduction_self_test:")
    test_known_reducible_hit()
    test_known_miss_silent()
    test_out_of_scope()
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
