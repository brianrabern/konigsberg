"""Smoke tests for fidelity-gate scripts (imports / conventions / self-test)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_CI = _ROOT / "ci"


def _load(name: str):
    path = _CI / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_check_imports_ok_on_formal() -> None:
    assert _load("check_imports").main(str(_ROOT / "formal")) == 0


def test_check_conventions_ok_on_formal() -> None:
    assert _load("check_conventions").main(str(_ROOT / "formal")) == 0


def test_self_test_audit_ok() -> None:
    assert _load("self_test_audit").main() == 0
