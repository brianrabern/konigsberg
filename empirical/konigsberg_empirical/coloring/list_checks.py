"""List-coloring / choosability checks over the canonical Graph representation.

Two tiers of difficulty, kept honest:

* `is_L_colorable` (a coloring for GIVEN lists) and ordinary `is_k_colorable` /
  `chromatic_number` are polynomial-space backtracking searches — correct and
  fast for the small graphs this tier targets.

* `is_k_choosable` quantifies over ALL list assignments, which is the coNP-hard
  core the specialized solvers (Alon-Tarsi, fixer-breaker; see M4) exist to
  attack. Here it is an EXHAUSTIVE decision procedure with a hard tractability
  guard: exact for tiny graphs, and it raises rather than hang or approximate.
  Do not use it as the production choosability oracle — that is the ported
  solver's job.
"""
from __future__ import annotations

from collections.abc import Sequence
from itertools import combinations, product

from ..core import Graph

# Max number of list assignments is_k_choosable will enumerate before refusing.
# Keeps the exhaustive path honest: it answers exactly or not at all.
CHOOSABILITY_ASSIGNMENT_LIMIT = 2_000_000


def is_L_colorable(graph: Graph, lists: Sequence[set[int]]) -> bool:
    """True iff G has a proper coloring c with c(v) in lists[v].

    Backtracking with a most-constrained-vertex order (smallest list first, then
    highest degree) for early pruning. Correct and cheap for small graphs.
    """
    if len(lists) != graph.n:
        raise ValueError(f"expected {graph.n} lists, got {len(lists)}")
    adj = [graph.neighbors(v) for v in range(graph.n)]
    order = sorted(range(graph.n), key=lambda v: (len(lists[v]), -len(adj[v])))
    color: list[int | None] = [None] * graph.n

    def extend(i: int) -> bool:
        if i == len(order):
            return True
        v = order[i]
        for c in lists[v]:
            if all(color[w] != c for w in adj[v]):
                color[v] = c
                if extend(i + 1):
                    return True
                color[v] = None
        return False

    return extend(0)


def is_k_colorable(graph: Graph, k: int) -> bool:
    """Ordinary proper k-colorability (every vertex shares the same k colors)."""
    if k <= 0:
        return graph.n == 0
    return is_L_colorable(graph, [set(range(k)) for _ in range(graph.n)])


def chromatic_number(graph: Graph) -> int:
    """Smallest k with a proper k-coloring."""
    if graph.n == 0:
        return 0
    for k in range(1, graph.n + 1):
        if is_k_colorable(graph, k):
            return k
    return graph.n  # unreachable for a simple graph, but a safe floor


def is_k_choosable(
    graph: Graph, k: int, *, limit: int = CHOOSABILITY_ASSIGNMENT_LIMIT
) -> bool:
    """Exact k-choosability by exhaustive search. Small graphs only.

    G is k-choosable iff every assignment of k-element lists admits a proper
    coloring. Any bad assignment's colors fit in a universe of size k*n, and by
    relabeling we may fix vertex 0's list to {0,...,k-1} (choosability is invariant
    under color renaming) — cutting the search by one vertex's worth of choices.

    Raises ValueError if the assignment count would exceed `limit`, rather than
    hang: for anything past tiny graphs, use the specialized solver (M4).
    """
    n = graph.n
    if n == 0:
        return True
    if k <= 0:
        return False  # some vertex gets an empty list -> uncolorable
    palette = range(k * n)  # large enough to hold any k-list assignment's union
    k_lists = [set(c) for c in combinations(palette, k)]

    assignments = len(k_lists) ** (n - 1)
    if assignments > limit:
        raise ValueError(
            f"choosability search too large: {assignments} assignments > {limit} "
            f"for n={n}, k={k}; use the specialized solver instead"
        )

    fixed = set(range(k))  # vertex 0's list, fixed by symmetry
    for rest in product(k_lists, repeat=n - 1):
        if not is_L_colorable(graph, [fixed, *rest]):
            return False
    return True
