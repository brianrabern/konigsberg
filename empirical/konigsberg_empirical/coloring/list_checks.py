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

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from itertools import combinations, product

from ..core import Graph

# Max number of list assignments is_k_choosable will enumerate before refusing.
# Keeps the exhaustive path honest: it answers exactly or not at all.
CHOOSABILITY_ASSIGNMENT_LIMIT = 2_000_000


def find_list_coloring(graph: Graph, lists: Sequence[set[int]]) -> dict[int, int] | None:
    """Return a proper coloring {v: color} with color(v) in lists[v], or None.

    Backtracking with a most-constrained-vertex order (smallest list first, then
    highest degree) for early pruning. Correct and cheap for small graphs. The
    witness it returns is what CEGAR choosability search needs to refine on.
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

    if not extend(0):
        return None
    return {v: c for v, c in enumerate(color) if c is not None}


def is_L_colorable(graph: Graph, lists: Sequence[set[int]]) -> bool:
    """True iff G has a proper coloring c with c(v) in lists[v]."""
    return find_list_coloring(graph, lists) is not None


def is_k_colorable(graph: Graph, k: int) -> bool:
    """Ordinary proper k-colorability (every vertex shares the same k colors)."""
    if k <= 0:
        return graph.n == 0
    return is_L_colorable(graph, [set(range(k)) for _ in range(graph.n)])


def find_k_coloring(graph: Graph, k: int) -> list[int] | None:
    """Return a proper k-coloring as a list indexed by vertex, or None."""
    if k <= 0:
        return [] if graph.n == 0 else None
    found = find_list_coloring(graph, [set(range(k)) for _ in range(graph.n)])
    if found is None:
        return None
    return [found[v] for v in range(graph.n)]


def is_proper_coloring(graph: Graph, coloring: Sequence[int], *, k: int | None = None) -> bool:
    """True iff `coloring` is a proper vertex coloring (optionally using colors in 0..k-1)."""
    if len(coloring) != graph.n:
        return False
    if k is not None and any(c < 0 or c >= k for c in coloring):
        return False
    return all(coloring[u] != coloring[v] for u, v in graph.edges)


def find_clique(graph: Graph, size: int) -> list[int] | None:
    """Return `size` pairwise-adjacent vertices, or None. Exhaustive; small n only."""
    if size <= 0:
        return []
    if size == 1:
        return [0] if graph.n else None
    for verts in combinations(range(graph.n), size):
        if all(tuple(sorted((a, b))) in graph.edges for a, b in combinations(verts, 2)):
            return list(verts)
    return None


def verify_clique(graph: Graph, verts: Sequence[int]) -> bool:
    """Independent check that `verts` induce a clique."""
    vs = list(verts)
    return all(
        i == j or tuple(sorted((vs[i], vs[j]))) in graph.edges
        for i in range(len(vs))
        for j in range(len(vs))
    )


def find_odd_cycle(graph: Graph) -> list[int] | None:
    """Return an odd cycle (vertex list) if G is not bipartite, else None."""
    color = [-1] * graph.n
    parent: dict[int, int] = {}
    for start in range(graph.n):
        if color[start] >= 0:
            continue
        color[start] = 0
        stack = [start]
        while stack:
            u = stack.pop()
            for v in graph.neighbors(u):
                if color[v] < 0:
                    color[v] = 1 - color[u]
                    parent[v] = u
                    stack.append(v)
                elif color[v] == color[u] and parent.get(u) != v:
                    cycle = _odd_cycle_through(u, v, parent)
                    if cycle is not None and verify_odd_cycle(graph, cycle):
                        return cycle
    return None


def _odd_cycle_through(u: int, v: int, parent: dict[int, int]) -> list[int] | None:
    """Reconstruct the fundamental cycle of tree-edge conflict (u, v)."""

    def ancestors(x: int) -> list[int]:
        chain = [x]
        while x in parent:
            x = parent[x]
            chain.append(x)
        return chain

    pu, pv = ancestors(u), ancestors(v)
    sv = set(pv)
    i = 0
    while i < len(pu) and pu[i] not in sv:
        i += 1
    if i >= len(pu):
        return None
    lca = pu[i]
    j = pv.index(lca)
    cycle = pu[: i + 1] + list(reversed(pv[:j]))
    return cycle if len(cycle) % 2 == 1 and len(cycle) >= 3 else None


def verify_odd_cycle(graph: Graph, cycle: Sequence[int]) -> bool:
    """Independent check: simple odd cycle with all consecutive edges (incl. close)."""
    n = len(cycle)
    if n < 3 or n % 2 == 0 or len(set(cycle)) != n:
        return False
    for i in range(n):
        a, b = cycle[i], cycle[(i + 1) % n]
        if tuple(sorted((a, b))) not in graph.edges:
            return False
    return True


def find_noncolorability_obstruction(
    graph: Graph, k: int
) -> tuple[str, list[int]] | None:
    """Re-checkable witness that G is not k-colorable, if a standard obstruction is found.

    Returns (kind, verts) where kind is \"clique\" (K_{k+1}) or \"odd_cycle\" (k=2 only).
    """
    if k < 0:
        return None
    clique = find_clique(graph, k + 1)
    if clique is not None and verify_clique(graph, clique):
        return ("clique", clique)
    if k == 2:
        cycle = find_odd_cycle(graph)
        if cycle is not None and verify_odd_cycle(graph, cycle):
            return ("odd_cycle", cycle)
    return None


def chromatic_number(graph: Graph) -> int:
    """Smallest k with a proper k-coloring."""
    if graph.n == 0:
        return 0
    for k in range(1, graph.n + 1):
        if is_k_colorable(graph, k):
            return k
    return graph.n  # unreachable for a simple graph, but a safe floor


def clique_number_witness(graph: Graph) -> tuple[int, list[int]]:
    """Return (ω(G), witnessing clique). Exhaustive; intended for small n."""
    if graph.n == 0:
        return 0, []
    for size in range(graph.n, 0, -1):
        clique = find_clique(graph, size)
        if clique is not None:
            return size, clique
    return 1, [0]


@dataclass(frozen=True)
class ChromaticCertificates:
    """Honest χ: coloring (upper) + not-(χ−1) obstruction/decision (lower)."""

    chi: int
    coloring: list[int]
    omega: int
    clique: list[int]
    lower_detail: str  # human-readable not-(χ−1) certificate
    lower_kind: str  # "clique" | "odd_cycle" | "unsat" | "none"


def _find_coloring(graph: Graph, k: int) -> list[int] | None:
    """Prefer SAT when available; else backtracking."""
    try:
        from ..search import sat

        if sat.is_available():
            return sat.sat_find_k_coloring(graph, k)
    except ImportError:
        pass
    return find_k_coloring(graph, k)


def chromatic_certificates(graph: Graph) -> ChromaticCertificates:
    """Compute χ with both directions: χ-coloring and not-(χ−1) evidence.

    Searches upward from ω. Lower bound prefers a re-checkable obstruction
    (clique / odd cycle); else records a complete UNSAT decision.
    """
    omega, clique = clique_number_witness(graph)
    if graph.n == 0:
        return ChromaticCertificates(0, [], 0, [], "empty graph", "none")

    lo = max(omega, 1)
    coloring: list[int] | None = None
    chi = graph.n
    for k in range(lo, graph.n + 1):
        coloring = _find_coloring(graph, k)
        if coloring is not None:
            chi = k
            break
    if coloring is None:
        coloring = list(range(graph.n))
        chi = graph.n

    if chi <= 1:
        return ChromaticCertificates(
            chi, list(coloring), omega, clique, "no lower bound (χ≤1)", "none"
        )

    obs = find_noncolorability_obstruction(graph, chi - 1)
    if obs is not None:
        kind, verts = obs
        if kind == "clique":
            detail = f"clique K_{chi} on {verts}"
        else:
            detail = f"odd cycle {verts}"
        return ChromaticCertificates(
            chi, list(coloring), omega, clique, detail, kind
        )

    # Completeness of the decision procedure for (χ−1)-colorability.
    assert _find_coloring(graph, chi - 1) is None
    return ChromaticCertificates(
        chi,
        list(coloring),
        omega,
        clique,
        f"complete UNSAT for {chi - 1}-colorability",
        "unsat",
    )


def verify_chromatic_bundle(graph: Graph, certs: ChromaticCertificates) -> bool:
    """Independently re-check a ChromaticCertificates bundle."""
    if not verify_clique(graph, certs.clique):
        return False
    if len(certs.clique) != certs.omega and not (
        certs.omega == 0 and graph.n == 0
    ):
        return False
    if not is_proper_coloring(graph, certs.coloring, k=certs.chi):
        return False
    if certs.chi <= 1:
        return True
    if certs.lower_kind == "clique":
        # Clique of size χ forbids (χ−1)-colorability.
        return find_clique(graph, certs.chi) is not None
    if certs.lower_kind == "odd_cycle":
        return find_odd_cycle(graph) is not None and certs.chi == 3
    if certs.lower_kind == "unsat":
        return _find_coloring(graph, certs.chi - 1) is None
    return certs.lower_kind == "none"


def is_k_choosable(
    graph: Graph,
    k: int,
    *,
    limit: int = CHOOSABILITY_ASSIGNMENT_LIMIT,
    colorable: Callable[[Graph, Sequence[set[int]]], bool] = is_L_colorable,
) -> bool:
    """Exact k-choosability by exhaustive search. Small graphs only.

    G is k-choosable iff every assignment of k-element lists admits a proper
    coloring. Any bad assignment's colors fit in a universe of size k*n, and by
    relabeling we may fix vertex 0's list to {0,...,k-1} (choosability is invariant
    under color renaming) — cutting the search by one vertex's worth of choices.

    The per-assignment colorability check is injected via `colorable` so the SAT
    backend (sat.sat_L_colorable) can be dropped in to push the tractable range
    outward; the default is the pure backtracking check. Either way the OUTER
    search is exhaustive over assignments — SAT scales the inner instance, not the
    Pi-2 quantifier.

    Raises ValueError if the assignment count would exceed `limit`, rather than
    hang.
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
            f"for n={n}, k={k}; raise `limit` or use a specialized solver"
        )

    fixed = set(range(k))  # vertex 0's list, fixed by symmetry
    for rest in product(k_lists, repeat=n - 1):
        if not colorable(graph, [fixed, *rest]):
            return False
    return True
