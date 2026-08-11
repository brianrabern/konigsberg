#!/usr/bin/env python3
"""self_test_audit — prove check_no_sorry / check_axioms are not no-ops.

Plants throwaway status.toml + Proofs.lean fixtures containing (a) sorry,
(b) a non-whitelisted recorded axiom, and (c) Lean.ofReduceBool (native_decide),
and asserts each gate rejects them. Fail CI if any slips through.

Usage:  python ci/self_test_audit.py
Exit:   0 pass, 1 self-test failure.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path

_CI = Path(__file__).resolve().parent


def _load(name: str):
    path = _CI / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


check_no_sorry = _load("check_no_sorry")
check_axioms = _load("check_axioms")


def _write_entry(root: Path, name: str, status_body: str, proofs_body: str) -> None:
    d = root / "Konigsberg" / "Literature" / "Coloring" / name
    d.mkdir(parents=True)
    (d / "status.toml").write_text(status_body)
    (d / "Proofs.lean").write_text(proofs_body)


def main() -> int:
    failures = 0
    with tempfile.TemporaryDirectory(prefix="konigsberg-self-test-") as tmp:
        root = Path(tmp) / "formal"
        root.mkdir()

        _write_entry(
            root,
            "PlantedSorry",
            """
[entry]
name = "PlantedSorry"
citation = "self-test"
area = "coloring"

[[claims]]
lean_name = "Konigsberg.Literature.Coloring.PlantedSorry.planted"
status = "formalized"
verified_at = "1970-01-01"
axioms = []
""".lstrip(),
            "theorem planted : True := by sorry\n",
        )
        if check_no_sorry.main(str(root)) == 0:
            print("self_test_audit: FAIL — check_no_sorry accepted a planted sorry")
            failures += 1
        else:
            print("self_test_audit: check_no_sorry rejected planted sorry")

        shutil.rmtree(root)
        root.mkdir()

        _write_entry(
            root,
            "PlantedAxiom",
            """
[entry]
name = "PlantedAxiom"
citation = "self-test"
area = "coloring"

[[claims]]
lean_name = "Konigsberg.Literature.Coloring.PlantedAxiom.planted"
status = "formalized"
verified_at = "1970-01-01"
axioms = ["PlantedLocalAxiom"]
""".lstrip(),
            "-- axioms recorded in status.toml\n",
        )
        if check_axioms.main([str(root)]) == 0:
            print("self_test_audit: FAIL — check_axioms accepted a planted local axiom")
            failures += 1
        else:
            print("self_test_audit: check_axioms rejected planted local axiom")

        shutil.rmtree(root)
        root.mkdir()

        _write_entry(
            root,
            "PlantedNativeDecide",
            """
[entry]
name = "PlantedNativeDecide"
citation = "self-test"
area = "coloring"

[[claims]]
lean_name = "Konigsberg.Literature.Coloring.PlantedNativeDecide.planted"
status = "formalized"
verified_at = "1970-01-01"
axioms = ["Lean.ofReduceBool"]
""".lstrip(),
            "-- native_decide → Lean.ofReduceBool in #print axioms\n",
        )
        if check_axioms.main([str(root)]) == 0:
            print(
                "self_test_audit: FAIL — check_axioms accepted planted Lean.ofReduceBool"
            )
            failures += 1
        else:
            print("self_test_audit: check_axioms rejected planted Lean.ofReduceBool")

    if failures:
        print(f"self_test_audit: FAIL ({failures} case(s))")
        return 1
    print("self_test_audit: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
