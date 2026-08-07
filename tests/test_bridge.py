"""Bridge encoder (offline) + live Lean roundtrip/verify (skipped without a build)."""
from __future__ import annotations

from pathlib import Path

import pytest
from konigsberg_empirical.core import Graph
from konigsberg_harness.ledger import TrustRoot
from konigsberg_harness.tools.bridge import (
    _parse_edge_list,
    export_graph_to_lean,
    roundtrip_check,
    verify_coloring,
)

FORMAL = Path("formal")
_LEAN_BUILT = (FORMAL / ".lake" / "packages" / "mathlib").is_dir()
needs_lean = pytest.mark.skipif(not _LEAN_BUILT, reason="formal/.lake not built")


# --- export_graph_to_lean (pure) ------------------------------------------

def test_export_path_shape():
    g = Graph.of(3, [(0, 1), (1, 2)])
    src = export_graph_to_lean(g, "G")
    assert "def G_E : Finset (Sym2 (Fin 3))" in src
    assert "s(0, 1)" in src and "s(1, 2)" in src
    assert "SimpleGraph.fromEdgeSet ↑G_E" in src
    assert "DecidableRel G.Adj" in src
    assert "decidable_of_iff" in src


def test_export_empty_graph():
    g = Graph.of(2, [])
    src = export_graph_to_lean(g, "H")
    assert "Fin 2" in src
    assert "∅" in src


def test_export_rejects_bad_name():
    with pytest.raises(ValueError, match="identifier"):
        export_graph_to_lean(Graph.of(1, []), "G-1")


def test_parse_edge_list_from_eval_output():
    assert _parse_edge_list("[(0, 1), (1, 2)]") == frozenset({(0, 1), (1, 2)})
    assert _parse_edge_list("info: [(2, 0)]") == frozenset({(0, 2)})


# --- live Lean ------------------------------------------------------------

@needs_lean
def test_roundtrip_path():
    from konigsberg_harness.lean_repl import LeanREPL

    g = Graph.of(3, [(0, 1), (1, 2)])
    with LeanREPL(project_dir="formal", timeout_s=180) as repl:
        assert roundtrip_check(g, repl) is True


@needs_lean
def test_roundtrip_empty_and_complete_small():
    from konigsberg_harness.lean_repl import LeanREPL

    with LeanREPL(project_dir="formal", timeout_s=180) as repl:
        assert roundtrip_check(Graph.of(1, []), repl) is True
        assert roundtrip_check(Graph.of(3, [(0, 1), (0, 2), (1, 2)]), repl) is True


@needs_lean
def test_verify_coloring_path_proper():
    from konigsberg_harness.lean_repl import LeanREPL

    # P3 path: graph6 "Bg", proper 2-coloring
    g6 = "Bg"
    coloring = [0, 1, 0]
    with LeanREPL(project_dir="formal", timeout_s=180) as repl:
        claim = verify_coloring(g6, coloring, repl=repl)
    assert claim.provenance.trust_root is TrustRoot.LEAN_KERNEL
    assert claim.provenance.label() == "proved"
    assert "sorryAx" not in claim.provenance.axioms
    assert claim.provenance.tool == "verify_coloring"


@needs_lean
def test_verify_coloring_rejects_bad_coloring():
    from konigsberg_harness.lean_repl import LeanREPL

    with (
        LeanREPL(project_dir="formal", timeout_s=180) as repl,
        pytest.raises(ValueError, match="coloring not accepted"),
    ):
        verify_coloring("Bg", [0, 0, 0], repl=repl)
