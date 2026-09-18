#!/usr/bin/env python3
"""Retro-referee the formalized BK reducibility bridge. Does not /promote.

``Konigsberg.Literature.Coloring.BK_ReducibleOfFChoosable.reducible_of_fChoosable``
is already ``formalized``. ``make gates`` runs the planted-flaw referee fixture
(``ci/referee_self_test.py``), not a review of this theorem. Promotion into the
corpus stays human-gated.

Run:  uv run python scripts/referee_bridge.py
Exit: 0 after a report (accept or not — this step is ungated).
      1 if Lean is missing or ``#check`` / ``#print axioms`` fails.
"""
from __future__ import annotations

import sys

from konigsberg_harness.envfile import load_project_env
from konigsberg_harness.lean_repl import LeanREPL, LeanREPLError
from konigsberg_harness.ledger import mint_lean_proof
from konigsberg_harness.models import has_live_provider
from konigsberg_harness.referee import build_referee_model, run_referee
from konigsberg_harness.tools.registry import build_registry

BRIDGE = (
    "Konigsberg.Literature.Coloring.BK_ReducibleOfFChoosable.reducible_of_fChoosable"
)


def main() -> int:
    load_project_env()
    print(f"retro-refereeing {BRIDGE}")
    print("will not /promote — Literature write-back stays human-gated")
    repl = LeanREPL(project_dir="formal", timeout_s=300)
    try:
        repl.start()
        repl.ensure_preamble(timeout_s=300)
        checked = repl.send(f"#check {BRIDGE}", commit=False)
        if checked.errors:
            print("FAIL: #check\n" + "\n".join(checked.errors))
            return 1
        axioms = tuple(repl.print_axioms(BRIDGE))
        print(f"kernel #check ok; axioms={list(axioms)}")
        claim = mint_lean_proof(BRIDGE, axioms, tool="lean_prove", durable=True)
        registry = build_registry(repl)
        model = build_referee_model() if has_live_provider() else None
        if model is None:
            print("no live model — heuristic checks only (not adversarial)")
        report = run_referee(
            claim,
            registry=registry,
            model=model,
            ledger_claims=(claim,),
            repl=repl,
        )
        print()
        print(report.render())
        print()
        if report.allows_promotion():
            print("recommendation: accept — still do not /promote (already in corpus)")
        else:
            print(
                f"recommendation: {report.recommendation} — not a CI gate; "
                "do not /promote"
            )
        return 0
    except LeanREPLError as e:
        print(f"FAIL: {e}")
        return 1
    finally:
        repl.close()


if __name__ == "__main__":
    sys.exit(main())
