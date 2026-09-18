"""Unit tests for preamble bookkeeping + live probe that ℕ/omega works."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from konigsberg_harness.lean_repl import (
    DEFAULT_SCRATCH_PREAMBLE,
    LeanREPL,
    library_oleans_stale,
)
from konigsberg_harness.ledger import TrustRoot
from konigsberg_harness.tools.lean_tools import lean_check, lean_prove

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


def test_library_oleans_stale_when_olean_missing(tmp_path):
    (tmp_path / "Konigsberg.lean").write_text("import Konigsberg.Literature\n")
    assert library_oleans_stale(tmp_path) is True


def test_library_oleans_stale_when_source_newer(tmp_path):
    olean = tmp_path / ".lake" / "build" / "lib" / "lean" / "Konigsberg.olean"
    olean.parent.mkdir(parents=True)
    olean.write_bytes(b"fake")
    src = tmp_path / "Konigsberg" / "Literature.lean"
    src.parent.mkdir()
    src.write_text("-- newer\n")
    # Source mtime after olean.
    newer = olean.stat().st_mtime + 10
    os.utime(src, (newer, newer))
    assert library_oleans_stale(tmp_path) is True


def test_library_oleans_fresh_when_olean_newer(tmp_path):
    src = tmp_path / "Konigsberg.lean"
    src.write_text("import Konigsberg.Literature\n")
    olean = tmp_path / ".lake" / "build" / "lib" / "lean" / "Konigsberg.olean"
    olean.parent.mkdir(parents=True)
    olean.write_bytes(b"fake")
    newer = src.stat().st_mtime + 10
    os.utime(olean, (newer, newer))
    assert library_oleans_stale(tmp_path) is False


def test_new_env_clears_preamble_flag():
    with LeanREPL(repl_cmd=[sys.executable, "-c", FAKE_REPL], timeout_s=5) as repl:
        repl._preamble_loaded = True
        repl.send("def x := 1", new_env=True)
        assert repl._preamble_loaded is False


def test_send_commit_false_leaves_env_pointer():
    with LeanREPL(repl_cmd=[sys.executable, "-c", FAKE_REPL], timeout_s=5) as repl:
        repl.send("def a := 1")  # env becomes 0 in fake
        before = repl._env
        repl.send("def b := 2", commit=False)
        assert repl._env == before


def test_send_transactional_commits_only_on_ok():
    # Fake always returns ok; commit path records session cmds.
    with LeanREPL(repl_cmd=[sys.executable, "-c", FAKE_REPL], timeout_s=5) as repl:
        repl.load_preamble("import Fake")
        assert repl._session_cmds == []
        repl.send_transactional("theorem t : True := trivial")
        assert len(repl._session_cmds) == 1
        assert "theorem t" in repl._session_cmds[0]


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


@needs_lean
def test_scratch_preamble_sees_literature_theorems():
    """Stale Konigsberg.olean used to hide Literature names from lean_check."""
    with LeanREPL(project_dir="formal", timeout_s=300) as repl:
        gs = lean_check(
            repl,
            "#check @Konigsberg.Literature.Coloring."
            "BK_ReducibleOfFChoosable.reducible_of_fChoosable",
        )
    assert gs.ok
    assert not gs.errors
    assert any("reducible_of_fChoosable" in info for info in gs.infos)
