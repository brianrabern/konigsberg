"""SAT encodings for coloring decisions — the complete solver core.

k-colorability and L-colorability are NP decision problems: exactly what a SAT
solver eats. This is the layer that scales refutation from the brute-force
ceiling (n<=7 without nauty) to graphs with dozens of vertices, and it is the
inner primitive that lets choosability *search* scale (each candidate list
assignment is one SAT call — see list_checks.is_k_choosable).

Encoding (standard, minimal):
  * variable x[v,c] = "vertex v takes color c", for c in v's allowed colors;
  * ALO: each vertex takes at least one color;
  * for every edge (u,v) and shared color c: not (x[u,c] and x[v,c]).
No at-most-one clauses are needed: adjacent vertices can never share a color, so
picking any satisfied color per vertex yields a proper coloring.

Completeness note for the ledger: SAT decides k-/L-colorability EXACTLY (a
`python-checked`-strength result up to the stated n). It does NOT decide
k-choosability, which quantifies over all list assignments (Pi-2); SAT only
answers each inner instance.

python-sat is an optional dependency (extra `sat`); import is deferred so the
rest of the empirical tier works without it.
"""
from __future__ import annotations

from collections.abc import Sequence

from ..core import Graph


def is_available() -> bool:
    """True iff the python-sat backend can be imported."""
    try:
        import pysat  # noqa: F401
    except ImportError:
        return False
    return True


def _solve(n: int, allowed: list[set[int]], edges: frozenset[tuple[int, int]]) -> bool:
    """Return True iff a proper coloring exists with color(v) in allowed[v]."""
    # A vertex with no available color makes the instance immediately unsatisfiable.
    if any(len(allowed[v]) == 0 for v in range(n)):
        return False

    from pysat.formula import IDPool
    from pysat.solvers import Minisat22

    pool = IDPool()

    def var(v: int, c: int) -> int:
        return pool.id(("x", v, c))

    cnf: list[list[int]] = []
    for v in range(n):
        cnf.append([var(v, c) for c in allowed[v]])  # at least one color
    for u, w in edges:
        for c in allowed[u] & allowed[w]:  # forbid a shared color on an edge
            cnf.append([-var(u, c), -var(w, c)])

    with Minisat22(bootstrap_with=cnf) as solver:
        return solver.solve()


def sat_k_colorable(graph: Graph, k: int) -> bool:
    """SAT-decide ordinary proper k-colorability. Complete; scales past brute force."""
    if k <= 0:
        return graph.n == 0
    palette = set(range(k))
    return _solve(graph.n, [set(palette) for _ in range(graph.n)], graph.edges)


def sat_L_colorable(graph: Graph, lists: Sequence[set[int]]) -> bool:
    """SAT-decide colorability for a GIVEN list assignment (one choosability instance)."""
    if len(lists) != graph.n:
        raise ValueError(f"expected {graph.n} lists, got {len(lists)}")
    return _solve(graph.n, [set(x) for x in lists], graph.edges)


# Backwards-compatible alias for the original stub name.
def sat_query(graph: Graph, k: int) -> bool:
    return sat_k_colorable(graph, k)
