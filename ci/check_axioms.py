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
              `#print axioms <lean_name>` (harness LeanREPL), assert they MATCH
              the recorded field, then validate. This is the real gate. Requires
              a built `formal/` (lake exe cache get && lake build) and
              konigsberg_harness importable.

              For each status.toml, a FRESH REPL environment is created and the
              entry's Proofs (or Statements) module is imported before querying
              — `#print axioms X` fails unless X is loaded, and the root
              `Konigsberg` import does NOT pull in Literature entries. SanityChecks
              are skipped: `decide` on those files has been observed to kill the
              REPL mid-corpus. A dead REPL is recreated before the next entry
              so one crash cannot poison the rest of the gate.

Usage:  python ci/check_axioms.py [ROOT=formal] [--run-lean] [--timeout=SECONDS]
Exit:   0 pass, 1 violation, 2 usage/parse error.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

WHITELIST: frozenset[str] = frozenset({"propext", "Classical.choice", "Quot.sound"})

DEFAULT_TIMEOUT_S = 120.0  # imports load oleans; generous vs the REPL's default


def validate(axioms: list[str], justified: set[str]) -> list[str]:
    """Return the list of disallowed axioms (empty == pass)."""
    allowed = WHITELIST | justified
    return [a for a in axioms if a not in allowed]


_PREFERRED_LEAN = ("Proofs.lean", "Statements.lean")


def modules_for_status(status_path: Path, root_path: Path) -> list[str]:
    """Lean module names to import so this entry's declarations are in scope.

    Prefers ``Proofs.lean`` (which imports Statements) over a glob of every
    sibling ``*.lean``. ``SanityChecks.lean`` is skipped: those files can
    ``decide`` large graphs and have been observed to close the REPL stdout
    mid ``--run-lean``. Falls back to the library root ``Konigsberg`` when
    the entry keeps no local ``.lean`` file next to its status.toml.
    """
    parent = status_path.parent
    chosen: list[Path] = []
    for name in _PREFERRED_LEAN:
        p = parent / name
        if p.is_file():
            chosen.append(p)
            break
    if not chosen:
        chosen = sorted(
            p for p in parent.glob("*.lean") if p.name != "SanityChecks.lean"
        )
    if not chosen:
        return ["Konigsberg"]
    modules: list[str] = []
    for lean_file in chosen:
        rel = lean_file.relative_to(root_path).with_suffix("")
        modules.append(".".join(rel.parts))
    return modules


class _LeanAxiomProbe:
    """Thin wrapper over LeanREPL for the --run-lean path.

    Import is deferred to construction so the default (recorded) mode has no
    dependency on a built Lean env or the harness package.
    """

    def __init__(self, root: Path, timeout_s: float, repl: object | None = None) -> None:
        self._root = root
        self._timeout = timeout_s
        if repl is None:
            from konigsberg_harness.lean_repl import LeanREPL  # deferred on purpose

            repl = LeanREPL(project_dir=str(root), timeout_s=timeout_s)
        self._repl = repl

    def _recreate(self) -> None:
        """Drop a dead REPL so the next entry gets a live process."""
        closer = getattr(self._repl, "close", None)
        if closer is not None:
            try:
                closer()
            except Exception:  # noqa: BLE001, S110 — dead process; we are replacing it
                pass
        from konigsberg_harness.lean_repl import LeanREPL

        self._repl = LeanREPL(project_dir=str(self._root), timeout_s=self._timeout)

    def recover(self) -> None:
        """Best-effort new process after a failed load / #print axioms."""
        try:
            self._recreate()
        except Exception:  # noqa: BLE001, S110 — next load() will surface a fresh error
            pass

    def load(self, modules: list[str]) -> None:
        """Start a FRESH env with `modules` imported. Raises on import error."""
        try:
            self._repl.restart()
        except Exception:  # noqa: BLE001 — recreate a dead process, then retry
            self._recreate()
            self._repl.restart()
        src = "\n".join(f"import {m}" for m in modules)
        state = self._repl.send(src, timeout_s=self._timeout, new_env=True)
        if state.errors:
            raise RuntimeError("; ".join(state.errors))

    def axioms(self, lean_name: str) -> list[str]:
        return self._repl.print_axioms(lean_name, timeout_s=self._timeout)

    def close(self) -> None:
        closer = getattr(self._repl, "close", None)
        if closer is not None:
            closer()


def _parse_timeout(argv: list[str]) -> float:
    for a in argv:
        if a.startswith("--timeout="):
            return float(a.split("=", 1)[1])
    return DEFAULT_TIMEOUT_S


def main(argv: list[str]) -> int:
    run_lean = "--run-lean" in argv
    positional = [a for a in argv if not a.startswith("--")]
    root_path = Path(positional[0] if positional else "formal")
    if not root_path.exists():
        print(f"::error::root path does not exist: {root_path}")
        return 2

    probe: _LeanAxiomProbe | None = None
    if run_lean:
        try:
            probe = _LeanAxiomProbe(root_path, _parse_timeout(argv))
        except ImportError as e:
            print(f"::error::--run-lean needs konigsberg_harness importable: {e}")
            return 2

    violations = 0
    try:
        for status_path in sorted(root_path.rglob("status.toml")):
            try:
                data = tomllib.loads(status_path.read_text())
            except tomllib.TOMLDecodeError as e:
                print(f"::error file={status_path}::{e}")
                return 2

            formalized = [c for c in data.get("claims", []) if c.get("status") == "formalized"]
            if not formalized:
                continue
            justified = set(data.get("entry", {}).get("axioms_justification", {}).keys())

            if run_lean:
                assert probe is not None
                modules = modules_for_status(status_path, root_path)
                try:
                    probe.load(modules)
                except Exception as e:  # noqa: BLE001 — any failure taints the entry
                    print(
                        f"::error file={status_path}::could not import {modules}: {e}"
                    )
                    violations += len(formalized)
                    probe.recover()
                    continue

            for claim in formalized:
                name = claim.get("lean_name", "<unnamed>")
                recorded = list(claim.get("axioms", []))

                if run_lean:
                    assert probe is not None
                    try:
                        live = probe.axioms(name)
                    except Exception as e:  # noqa: BLE001 — unknown ident, timeout, dead REPL
                        print(f"::error file={status_path}::#print axioms {name}: {e}")
                        violations += 1
                        probe.recover()
                        continue
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
    finally:
        if probe is not None:
            probe.close()

    if violations:
        print(f"check_axioms: FAIL ({violations} violation(s))")
        return 1
    print("check_axioms: OK" + ("" if run_lean else " (recorded-axioms mode)"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
