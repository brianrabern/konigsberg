"""The empirical ↔ formal seam. The one place the two tiers meet.

A bug here looks AUTHORITATIVE ("decide confirmed it"), so the encoder gets the
same rigor as the solver port: round-trip property tests in CI
(Python graph → Lean → read back → assert equal under the identity labeling).

Honest scope: `decide` over `SimpleGraph.Colorable k` blows up; `native_decide`
is not whitelisted. The formal path here is for **finite witnesses on small
graphs** — export a concrete graph, and (when asked) re-check a *given* coloring
via `decide` on a quantifier-bounded, concrete proposition.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from konigsberg_empirical.core import Graph
from konigsberg_empirical.search.enumerate import parse_graph6

from ..ledger import Claim, mint_lean_proof

if TYPE_CHECKING:
    from ..lean_repl import LeanREPL

# Name used for the decide theorem inside verify_coloring snippets.
_COLORING_THM = "bridge_coloring_ok"

_EDGE_LIST_RE = re.compile(r"\[(.*?)\]", re.DOTALL)
_PAIR_RE = re.compile(r"\((\d+)\s*,\s*(\d+)\)")


def export_graph_to_lean(graph: Graph, name: str = "G") -> str:
    """Python `Graph` → Lean source defining `<name> : SimpleGraph (Fin n)`.

    Uses `SimpleGraph.fromEdgeSet` over a `Finset (Sym2 (Fin n))`. The fragile
    bit for REPL use is `DecidableRel Adj`: we emit an explicit instance via
    `decidable_of_iff` against Finset membership (Set membership alone does not
    synthesize).
    """
    if not name.isidentifier():
        raise ValueError(f"Lean declaration name must be an identifier, got {name!r}")
    n = graph.n
    edges_sorted = sorted(graph.edges)
    if edges_sorted:
        edge_lits = ", ".join(f"s({u}, {v})" for u, v in edges_sorted)
        edge_body = "{" + edge_lits + "}"
    else:
        edge_body = "∅"
    # `E` is a Finset so membership is decidable; coerce to Set for fromEdgeSet.
    return "\n".join(
        [
            f"def {name}_E : Finset (Sym2 (Fin {n})) := {edge_body}",
            f"def {name} : SimpleGraph (Fin {n}) := SimpleGraph.fromEdgeSet ↑{name}_E",
            f"instance : DecidableRel {name}.Adj := fun u v =>",
            f"  decidable_of_iff (s(u, v) ∈ {name}_E ∧ u ≠ v) (by",
            f"    simp [{name}, SimpleGraph.fromEdgeSet, Sym2.ToRel])",
        ]
    )


def _imports() -> str:
    return (
        "import Mathlib.Combinatorics.SimpleGraph.Basic\n"
        "import Mathlib.Combinatorics.SimpleGraph.Finite\n"
        "open SimpleGraph Finset"
    )


def _parse_edge_list(text: str) -> frozenset[tuple[int, int]]:
    """Parse `#eval` output like `[(0, 1), (1, 2)]` into a frozenset of pairs."""
    m = _EDGE_LIST_RE.search(text)
    if not m:
        raise ValueError(f"no edge list in REPL output: {text!r}")
    pairs = {
        tuple(sorted((int(a), int(b)))) for a, b in _PAIR_RE.findall(m.group(1))
    }
    return frozenset(pairs)


def _eval_edges_snippet(name: str, n: int) -> str:
    """Lean snippet whose `#eval` prints the upper-triangle edge list of `name`."""
    return "\n".join(
        [
            f"#eval ((List.finRange {n}).product (List.finRange {n})).filterMap fun p =>",
            "  let i := p.1; let j := p.2",
            f"  if i.val < j.val && decide ({name}.Adj i j) then some (i.val, j.val) else none",
        ]
    )


def _roundtrip_in_env(graph: Graph, repl: LeanREPL, name: str) -> bool:
    """Assume imports are already loaded; define `name` and compare edges."""
    src = "\n".join(
        [export_graph_to_lean(graph, name), _eval_edges_snippet(name, graph.n)]
    )
    state = repl.send(src, timeout_s=120)
    if not state.ok:
        raise ValueError(f"roundtrip Lean errors: {state.errors}")
    got = _parse_edge_list("\n".join(state.infos))
    return got == graph.edges


def roundtrip_check(graph: Graph, repl: LeanREPL) -> bool:
    """Export `graph`, load in `repl`, `#eval` adjacency, compare to input edges.

    Equality (not isomorphism): we control the 0..n-1 labeling. Returns True on
    match; raises on Lean errors. Skip at the call site when no Lean toolchain.
    """
    # Fresh env + imports: each standalone check is independent (`import` needs new_env).
    state = repl.send(_imports(), new_env=True, timeout_s=180)
    if not state.ok:
        raise ValueError(f"import failed: {state.errors}")
    return _roundtrip_in_env(graph, repl, "G")


def _coloring_def(name: str, n: int, coloring: list[int]) -> str:
    if len(coloring) != n:
        raise ValueError(f"coloring length {len(coloring)} != n={n}")
    if n == 0:
        return f"def {name} : Fin 0 → ℕ := fun _ => 0"
    lines = [f"def {name} : Fin {n} → ℕ"]
    for i, color in enumerate(coloring):
        lines.append(f"  | ⟨{i}, _⟩ => {int(color)}")
    return "\n".join(lines)


def verify_coloring(
    graph6: str,
    coloring: list[int],
    *,
    repl: LeanREPL,
) -> Claim:
    """Re-check a concrete coloring of `graph6` in the Lean kernel.

    Agent-callable args are JSON-native (`graph6` string + list of ℕ). On success
    mints a **proved** Claim (kernel re-checked the witness) carrying
    `#print axioms`. Does NOT call `decide` on `G.Colorable k`.
    """
    graph = parse_graph6(graph6)
    if len(coloring) != graph.n:
        raise ValueError(f"coloring length {len(coloring)} != n={graph.n}")
    color_def = _coloring_def("c", graph.n, coloring)
    thm = "\n".join(
        [
            f"theorem {_COLORING_THM} :",
            f"    ∀ ⦃u v : Fin {graph.n}⦄, G.Adj u v → c u ≠ c v := by decide",
        ]
    )
    src = "\n".join([_imports(), export_graph_to_lean(graph, "G"), color_def, thm])
    state = repl.send(src, new_env=True, timeout_s=120)
    if not state.ok:
        raise ValueError(f"coloring not accepted by decide: {state.errors}")
    axioms = tuple(repl.print_axioms(_COLORING_THM, timeout_s=60))
    stmt = f"{graph6} admits proper coloring {list(coloring)} (kernel-checked)"
    return mint_lean_proof(stmt, axioms, tool="verify_coloring")
