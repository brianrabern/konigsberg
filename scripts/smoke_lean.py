#!/usr/bin/env python3
"""M0 smoke test — prove the Lean environment round-trips through LeanREPL.

Verifies the three things milestone M0 actually claims:
  1. the `repl` exe launches inside the project's Lake env,
  2. the Konigsberg library (and therefore mathlib) imports,
  3. a trivial proof elaborates and its axioms are readable by the gate.

If this passes, `lean_check` round-trips and `check_axioms --run-lean` is live.

Prereq: `make lean-setup` (lake update + cache get + build). The first run also
compiles the small `repl` exe and loads mathlib oleans, so it can take a minute.

Run:   make lean-smoke        (or: uv run python scripts/smoke_lean.py)
Exit:  0 on success, 1 on failure.
"""
from __future__ import annotations

import sys

from konigsberg_harness.lean_repl import LeanREPL, LeanREPLError

SMOKE_THM = "konigsberg_smoke"


def main() -> int:
    # Generous timeout: first import loads mathlib oleans and the exe may still
    # be compiling on the first invocation.
    repl = LeanREPL(project_dir="formal", timeout_s=300)
    try:
        repl.start()

        imp = repl.send("import Konigsberg", new_env=True)
        if not imp.ok:
            print("FAIL: `import Konigsberg` errored:\n" + "\n".join(imp.errors))
            return 1

        thm = repl.send(f"theorem {SMOKE_THM} : True := trivial")
        if not thm.ok:
            print("FAIL: trivial theorem did not elaborate:\n" + "\n".join(thm.errors))
            return 1

        axioms = repl.print_axioms(SMOKE_THM)
        print("OK: import + elaborate + #print axioms round-trip.")
        print(f"    axioms of {SMOKE_THM}: {axioms or '[] (none)'}")
        return 0
    except LeanREPLError as e:
        print(f"FAIL: {e}")
        return 1
    finally:
        repl.close()


if __name__ == "__main__":
    sys.exit(main())
