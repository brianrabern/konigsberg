"""check_axioms: whitelist logic, module derivation, and the --run-lean wiring.

The live gate is exercised with a stub probe so the drift/validate logic is
covered without a built Lean env; the real REPL I/O is covered in test_lean_repl.
"""
import importlib.util
import types
from pathlib import Path

import pytest

# tomllib is stdlib on the project's target (3.11+); shim for older interpreters
# so the suite runs anywhere. No-ops where tomllib already exists.
try:  # pragma: no cover
    import tomllib  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover
    import sys

    import tomli

    sys.modules["tomllib"] = tomli

_CI = Path(__file__).resolve().parents[1] / "ci" / "check_axioms.py"
_spec = importlib.util.spec_from_file_location("check_axioms", _CI)
ca = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ca)


# --- validate -------------------------------------------------------------

def test_validate_accepts_whitelist():
    assert ca.validate(["propext", "Classical.choice", "Quot.sound"], set()) == []


def test_validate_flags_sorry_and_native_decide():
    assert ca.validate(["sorryAx"], set()) == ["sorryAx"]
    assert ca.validate(["Lean.ofReduceBool"], set()) == ["Lean.ofReduceBool"]


def test_validate_respects_per_case_justification():
    assert ca.validate(["Lean.ofReduceBool"], {"Lean.ofReduceBool"}) == []


# --- modules_for_status ---------------------------------------------------

def test_modules_from_sibling_lean_files(tmp_path: Path):
    root = tmp_path / "formal"
    entry = root / "Konigsberg" / "Literature" / "Coloring" / "Author_Result"
    entry.mkdir(parents=True)
    (entry / "Statements.lean").write_text("")
    (entry / "Proofs.lean").write_text("")
    status = entry / "status.toml"
    status.write_text("")
    mods = ca.modules_for_status(status, root)
    assert mods == [
        "Konigsberg.Literature.Coloring.Author_Result.Proofs",
        "Konigsberg.Literature.Coloring.Author_Result.Statements",
    ]


def test_modules_fallback_to_root_when_no_local_lean(tmp_path: Path):
    root = tmp_path / "formal"
    entry = root / "Konigsberg" / "Areas" / "Coloring"
    entry.mkdir(parents=True)
    status = entry / "status.toml"
    status.write_text("")
    assert ca.modules_for_status(status, root) == ["Konigsberg"]


# --- probe (stub repl) ----------------------------------------------------

class _StubRepl:
    def __init__(self, axioms_by_name, import_errors=()):
        self.axioms_by_name = axioms_by_name
        self.import_errors = list(import_errors)
        self.restarts = 0
        self.imported = None

    def restart(self):
        self.restarts += 1

    def send(self, src, timeout_s=None, new_env=False):
        self.imported = src
        return types.SimpleNamespace(errors=self.import_errors)

    def print_axioms(self, name, timeout_s=None):
        return self.axioms_by_name[name]

    def close(self):
        pass


def test_probe_load_imports_fresh_env_then_reports_axioms():
    repl = _StubRepl({"Foo.thm": ["propext"]})
    probe = ca._LeanAxiomProbe(Path("formal"), 10.0, repl=repl)
    probe.load(["Konigsberg.X.Proofs", "Konigsberg.X.Statements"])
    assert repl.restarts == 1
    assert repl.imported == "import Konigsberg.X.Proofs\nimport Konigsberg.X.Statements"
    assert probe.axioms("Foo.thm") == ["propext"]


def test_probe_load_raises_on_import_error():
    repl = _StubRepl({}, import_errors=["unknown module Foo"])
    probe = ca._LeanAxiomProbe(Path("formal"), 10.0, repl=repl)
    with pytest.raises(RuntimeError):
        probe.load(["Foo"])


# --- main: recorded mode --------------------------------------------------

def _write_entry(root: Path, *, status: str, axioms: list[str]):
    entry = root / "Konigsberg" / "Literature" / "Coloring" / "E"
    entry.mkdir(parents=True)
    (entry / "Proofs.lean").write_text("")
    axioms_toml = ", ".join(f'"{a}"' for a in axioms)
    (entry / "status.toml").write_text(
        "[entry]\nname='E'\ncitation='c'\narea='coloring'\n\n"
        "[[claims]]\n"
        'lean_name = "Konigsberg.Literature.Coloring.E.thm"\n'
        f'status = "{status}"\n'
        f"axioms = [{axioms_toml}]\n"
        'verified_at = "abc"\n'
    )


def test_main_recorded_mode_passes_clean_axioms(tmp_path: Path):
    root = tmp_path / "formal"
    _write_entry(root, status="formalized", axioms=["propext"])
    assert ca.main([str(root)]) == 0


def test_main_recorded_mode_fails_on_sorry(tmp_path: Path):
    root = tmp_path / "formal"
    _write_entry(root, status="formalized", axioms=["sorryAx"])
    assert ca.main([str(root)]) == 1


# --- main: --run-lean wiring (stub probe) ---------------------------------

def test_main_run_lean_detects_drift(tmp_path: Path, monkeypatch):
    root = tmp_path / "formal"
    _write_entry(root, status="formalized", axioms=["propext"])  # recorded

    class _StubProbe:
        def __init__(self, *_a, **_k):
            pass

        def load(self, modules):
            pass

        def axioms(self, name):
            return ["propext", "sorryAx"]  # live != recorded, and non-whitelisted

        def close(self):
            pass

    monkeypatch.setattr(ca, "_LeanAxiomProbe", _StubProbe)
    # drift (recorded propext vs live propext+sorryAx) + sorryAx not whitelisted
    assert ca.main([str(root), "--run-lean"]) == 1


def test_main_run_lean_passes_when_live_matches_and_clean(tmp_path: Path, monkeypatch):
    root = tmp_path / "formal"
    _write_entry(root, status="formalized", axioms=["propext"])

    class _StubProbe:
        def __init__(self, *_a, **_k):
            pass

        def load(self, modules):
            pass

        def axioms(self, name):
            return ["propext"]

        def close(self):
            pass

    monkeypatch.setattr(ca, "_LeanAxiomProbe", _StubProbe)
    assert ca.main([str(root), "--run-lean"]) == 0
