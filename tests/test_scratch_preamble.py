"""Unit tests for preamble bookkeeping + live probe that ℕ/omega works."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from konigsberg_harness.lean_repl import (
    DEFAULT_SCRATCH_PREAMBLE,
    LeanREPL,
)
from konigsberg_harness.ledger import TrustRoot
from konigsberg_harness.tools.lean_tools import lean_prove

FORMAL = Path("formal")
_LEAN_BUILT = (FORMAL / ".lake" / "packages" / "mathlib").is_dir()
needs_lean = pytest.mark.skipif(not _LEAN_BUILT, reason="formal/.lake not built")

# Minimal fake REPL (same contract as tests/test_lean_repl.py).
FAKE_REPL = r"""
import sys, json
buf = ""
for line in sys.stdin:
    if line.strip() == "":
        if buf.strip():
            obj = json.loads(buf)
            print(json.dumps({"env": 0, "echo": obj.get("cmd"),
                              "recv_env": obj.get("env", None),
                              "messages": [], "sorries": []}), flush=True)
            print(flush=True)
            buf = ""
    else:
        buf += line
"""


def test_scratch_preamble_imports_mathlib_and_konigsberg():
    assert "import Mathlib.Tactic" in DEFAULT_SCRATCH_PREAMBLE
    assert "import Konigsberg" in DEFAULT_SCRATCH_PREAMBLE
    assert "import Mathlib\n" not in DEFAULT_SCRATCH_PREAMBLE  # full Mathlib hangs startup
    assert "open SimpleGraph" in DEFAULT_SCRATCH_PREAMBLE
    assert "Konigsberg.Areas.Coloring" in DEFAULT_SCRATCH_PREAMBLE


def test_new_env_clears_preamble_flag():
    with LeanREPL(repl_cmd=[sys.executable, "-c", FAKE_REPL], timeout_s=5) as repl:
        repl._preamble_loaded = True
        repl.send("def x := 1", new_env=True)
        assert repl._preamble_loaded is False


def test_ensure_preamble_is_noop_when_already_loaded():
    with LeanREPL(repl_cmd=[sys.executable, "-c", FAKE_REPL], timeout_s=5) as repl:
        repl.load_preamble("import Fake")
        assert repl._preamble_loaded is True
        env_before = repl._env
        repl.ensure_preamble()  # should not re-send
        assert repl._env == env_before


@needs_lean
def test_lean_prove_nat_le_with_unicode_nat_and_omega():
    """Probe: Mathlib preamble makes `n : ℕ` + omega elaborate (the ℕ failure mode)."""
    with LeanREPL(project_dir="formal", timeout_s=300) as repl:
        claim = lean_prove(
            repl,
            "nat_le_example",
            "theorem nat_le_example (n : ℕ) : n ≤ n + 1 := by\n  omega",
        )
    assert claim.provenance.trust_root is TrustRoot.LEAN_KERNEL
    assert claim.provenance.label() == "proved"
    assert "sorryAx" not in claim.provenance.axioms
