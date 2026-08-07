"""Differential: bridge export round-trips under the identity labeling."""
from __future__ import annotations

from pathlib import Path

import pytest
from konigsberg_empirical.search.enumerate import all_graphs

FORMAL = Path("formal")
_LEAN_BUILT = (FORMAL / ".lake" / "packages" / "mathlib").is_dir()

pytestmark = pytest.mark.skipif(not _LEAN_BUILT, reason="formal/.lake not built")


@pytest.mark.parametrize("n", [1, 2, 3])
def test_roundtrip_all_graphs_small(n: int):
    from konigsberg_harness.lean_repl import LeanREPL
    from konigsberg_harness.tools.bridge import _imports, _roundtrip_in_env

    graphs = list(all_graphs(n))
    assert graphs  # atlas/geng should yield something
    with LeanREPL(project_dir="formal", timeout_s=300) as repl:
        imp = repl.send(_imports(), new_env=True, timeout_s=180)
        assert imp.ok, imp.errors
        for i, g in enumerate(graphs):
            assert _roundtrip_in_env(g, repl, f"G{n}_{i}"), (
                f"roundtrip failed for n={n} edges={sorted(g.edges)}"
            )
