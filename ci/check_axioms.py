#!/usr/bin/env python3
"""check_axioms — authoritative trust gate.

For every claim marked `formalized`, the axioms it actually depends on must fall
within the whitelist:

    propext, Classical.choice, Quot.sound

Anything else (notably `sorryAx`, which is how an unfinished proof shows up, and
`Lean.ofReduceBool`, which is how `native_decide` shows up) fails the build
unless explicitly whitelisted per-case with written justification recorded in
status.toml as `axioms_justification`.

Two modes:

  (default)   Validate the axioms RECORDED in each status.toml claim against the
              whitelist. Runnable in CI with no Lean build. Trusts the recorded
              field — which is only as good as the last --run-lean pass.

  --run-lean  Re-derive axioms from a live Lean environment via
              `#print axioms <lean_name>` and assert they MATCH the recorded
              field, then validate. This is the real gate. Requires a built
              `formal/` (lake exe cache get && lake build) and the harness
              lean_repl. Wire the call at the marked TODO.

Usage:  python ci/check_axioms.py [ROOT=formal] [--run-lean]
Exit:   0 pass, 1 violation, 2 usage/parse error.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

WHITELIST: frozenset[str] = frozenset({"propext", "Classical.choice", "Quot.sound"})


def derive_axioms_via_lean(lean_name: str) -> list[str]:
    """Return the axioms `#print axioms <lean_name>` reports.

    TODO(M1/M6): implement via harness.lean_repl.LeanREPL — send
    `#print axioms {lean_name}` to the persistent environment and parse the
    reported axiom list. Kept out of this module so the gate has no hard
    dependency on a built Lean env in --record-free mode.
    """
    raise NotImplementedError(
        "wire ci/check_axioms.py --run-lean to harness.lean_repl.LeanREPL"
    )


def validate(axioms: list[str], justified: set[str]) -> list[str]:
    """Return the list of disallowed axioms (empty == pass)."""
    allowed = WHITELIST | justified
    return [a for a in axioms if a not in allowed]


def main(argv: list[str]) -> int:
    run_lean = "--run-lean" in argv
    positional = [a for a in argv if not a.startswith("--")]
    root_path = Path(positional[0] if positional else "formal")
    if not root_path.exists():
        print(f"::error::root path does not exist: {root_path}")
        return 2

    violations = 0
    for status_path in sorted(root_path.rglob("status.toml")):
        try:
            data = tomllib.loads(status_path.read_text())
        except tomllib.TOMLDecodeError as e:
            print(f"::error file={status_path}::{e}")
            return 2

        justified = set(data.get("entry", {}).get("axioms_justification", {}).keys())

        for claim in data.get("claims", []):
            if claim.get("status") != "formalized":
                continue
            name = claim.get("lean_name", "<unnamed>")
            recorded = list(claim.get("axioms", []))

            if run_lean:
                try:
                    live = derive_axioms_via_lean(name)
                except NotImplementedError as e:
                    print(f"::error::--run-lean not wired yet: {e}")
                    return 2
                if sorted(live) != sorted(recorded):
                    print(
                        f"::error file={status_path}::axioms for {name} drifted — "
                        f"recorded {recorded}, live {live}"
                    )
                    violations += 1
                recorded = live

            bad = validate(recorded, justified)
            if bad:
                print(
                    f"::error file={status_path}::{name} uses non-whitelisted "
                    f"axiom(s): {bad}"
                )
                violations += 1

    if violations:
        print(f"check_axioms: FAIL ({violations} violation(s))")
        return 1
    print("check_axioms: OK" + ("" if run_lean else " (recorded-axioms mode)"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
