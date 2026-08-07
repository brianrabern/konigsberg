"""decide_colorable: ordinary k-colorability with witness / obstruction claims."""
from __future__ import annotations

import ast
import re
from pathlib import Path

import networkx as nx
import pytest
from konigsberg_empirical.coloring.list_checks import is_proper_coloring
from konigsberg_empirical.search.enumerate import all_graphs, parse_graph6
from konigsberg_harness.ledger import TrustRoot
from konigsberg_harness.tools.empirical_tools import decide_colorable
from konigsberg_harness.tools.registry import build_registry

_WITNESS_RE = re.compile(r"witness coloring (\[.*?\])")
FORMAL = Path("formal")
_LEAN_BUILT = (FORMAL / ".lake" / "packages" / "mathlib").is_dir()
needs_lean = pytest.mark.skipif(not _LEAN_BUILT, reason="formal/.lake not built")


def _g6_of(g) -> str:
    G = nx.empty_graph(g.n)
    G.add_edges_from(g.edges)
    return nx.to_graph6_bytes(G, header=False).decode().strip()


def _witness(claim) -> list[int]:
    m = _WITNESS_RE.search(claim.statement)
    assert m is not None, claim.statement
    return ast.literal_eval(m.group(1))


def test_decide_colorable_triangle_not_2_colorable():
    claim = decide_colorable("Bw", 2)
    assert "NOT 2-colorable" in claim.statement
    assert claim.provenance.trust_root is TrustRoot.CERTIFICATE
    assert claim.provenance.label() == "certificate-checked"
    assert "obstruction" in claim.statement


def test_decide_colorable_triangle_3_colorable_with_witness():
    claim = decide_colorable("Bw", 3)
    assert "is 3-colorable" in claim.statement
    assert claim.provenance.trust_root is TrustRoot.CERTIFICATE
    colors = _witness(claim)
    assert is_proper_coloring(parse_graph6("Bw"), colors, k=3)


def test_three_node_graphs_2_colorability():
    """The four graphs on 3 vertices: empty/one-edge/path yes; triangle no."""
    expected = {
        "B?": True,  # empty
        "B_": True,  # one edge
        "Bg": True,  # path P3
        "Bw": False,  # triangle
    }
    for g6, colorable in expected.items():
        claim = decide_colorable(g6, 2)
        if colorable:
            assert "is 2-colorable" in claim.statement
            assert is_proper_coloring(parse_graph6(g6), _witness(claim), k=2)
        else:
            assert "NOT 2-colorable" in claim.statement


def test_decide_colorable_registered_lean_free():
    reg = build_registry()
    assert "decide_colorable" in reg.names()
    specs = {s["name"]: s for s in reg.tool_specs()}
    assert "decide_colorable" in specs
    assert specs["decide_colorable"]["input_schema"]["properties"].keys() >= {
        "graph6",
        "k",
    }
    claim = reg.dispatch("decide_colorable", {"graph6": "Bw", "k": 2})
    assert "NOT 2-colorable" in claim.statement


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5])
@pytest.mark.parametrize("k", [1, 2, 3])
def test_witness_colorings_are_always_valid(n, k):
    for g in all_graphs(n):
        g6 = _g6_of(g)
        claim = decide_colorable(g6, k)
        if f"is {k}-colorable" in claim.statement:
            assert is_proper_coloring(g, _witness(claim), k=k)
        else:
            assert f"is NOT {k}-colorable" in claim.statement


@needs_lean
def test_decide_colorable_witness_upgrades_via_verify_coloring():
    from konigsberg_harness.lean_repl import LeanREPL
    from konigsberg_harness.tools.bridge import verify_coloring

    claim = decide_colorable("Bw", 3)
    colors = _witness(claim)
    with LeanREPL(project_dir="formal", timeout_s=180) as repl:
        proved = verify_coloring("Bw", colors, repl=repl)
    assert proved.provenance.trust_root is TrustRoot.LEAN_KERNEL
    assert proved.provenance.label() == "proved"
