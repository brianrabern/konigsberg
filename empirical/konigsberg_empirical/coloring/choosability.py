"""CEGAR choosability refutation — the offline-choosability engine.

Ported from Brian's bk.py / bk2.py and adapted to the canonical Graph type.

Instead of enumerating every k-list assignment (list_checks.is_k_choosable, which
is exact only for tiny graphs), this searches the assignment space with a SAT
solver, counterexample-guided:

    1. ask SAT for a candidate assignment L (each vertex gets exactly k colors);
    2. try to properly color G from L (backtracking, list_checks.find_list_coloring);
    3. if it CAN'T be colored, L is a certificate that G is not k-choosable — return it;
    4. if it can, with coloring sigma, add a blocking clause ruling out every
       assignment sigma would also color, and loop;
    5. when SAT is UNSAT, no bad assignment exists (up to the palette) — return None.

Trust, made precise:
  * A returned bad list is a CERTIFICATE: verify_bad_list re-checks it by
    independent backtracking, with no trust in the SAT machinery. -> certificate-checked.
  * A None result means "no bad list up to `palette` colors". With the default
    palette = k*n this is COMPLETE (any bad assignment's colors fit in k*n, so
    nothing is missed) — a genuine decision. A smaller palette is a faster,
    weaker bound: sound for refutations, not for the None verdict.

python-sat is a hard runtime dependency of konigsberg-empirical (CEGAR / SAT).
"""
from __future__ import annotations

from ..core import Graph
from .list_checks import find_list_coloring

DEFAULT_K = 3


def complete_palette(graph: Graph, k: int) -> int:
    """Palette size that makes a None result a complete decision."""
    return k * graph.n


def complete_palette_f(graph: Graph, f: dict[int, int]) -> int:
    """Palette size that makes a None result a complete f-choosability decision."""
    if graph.n == 0:
        return 0
    return max(f.values()) * graph.n


def _cardinality_clauses(n: int, palette: int, list_sizes: list[int], symmetry: bool):
    """Exactly list_sizes[v] colors per vertex v, plus optional symmetry breaking.

    Returns (clauses, var) where var(v, c) is the id of "color c is in L[v]".
    """
    from pysat.card import CardEnc, EncType

    if len(list_sizes) != n:
        raise ValueError(f"expected {n} list sizes, got {len(list_sizes)}")
    if any(sz < 0 for sz in list_sizes):
        raise ValueError("list sizes must be nonnegative")
    if palette < max(list_sizes, default=0):
        raise ValueError("palette smaller than some list size")

    def var(v: int, c: int) -> int:
        return v * palette + c + 1

    top = n * palette
    cnf: list[list[int]] = []
    for v in range(n):
        enc = CardEnc.equals(
            [var(v, c) for c in range(palette)],
            list_sizes[v],
            top_id=top,
            encoding=EncType.seqcounter,
        )
        cnf += enc.clauses
        top = max(top, enc.nv)

    if symmetry:
        # Value-precedence symmetry break: palette colors are interchangeable.
        # p[v][c] == "color c is listed by some vertex u <= v".
        p = [[0] * palette for _ in range(n)]
        for v in range(n):
            for c in range(palette):
                top += 1
                p[v][c] = top
        for v in range(n):
            for c in range(palette):
                pc, xc = p[v][c], var(v, c)
                if v == 0:
                    cnf += [[-pc, xc], [-xc, pc]]  # p[0][c] <-> x[0][c]
                else:
                    pp = p[v - 1][c]
                    cnf += [[-pc, pp, xc], [-pp, pc], [-xc, pc]]  # p[v][c] <-> p[v-1][c] v x[v][c]
        for v in range(n):
            for c in range(1, palette):
                cnf.append([-var(v, c), p[v][c - 1]])  # c usable at v only if c-1 already seen

    return cnf, var


def find_bad_list_f(
    graph: Graph,
    f: dict[int, int],
    *,
    palette: int | None = None,
    symmetry: bool = True,
) -> list[set[int]] | None:
    """An f-list assignment G cannot be colored from, or None if none exists.

    `f` maps each vertex to its required list size (worst-case slack). palette
    defaults to max(f)*n (complete). A returned list is an independently
    re-checkable certificate; None means no bad list up to `palette` colors.
    """
    n = graph.n
    if n == 0:
        return None
    if set(f) != set(range(n)):
        raise ValueError(f"f must cover vertices 0..{n - 1}, got {sorted(f)}")
    if any(fv < 1 for fv in f.values()):
        raise ValueError("every f(v) must be >= 1 for find_bad_list_f")
    if palette is None:
        palette = complete_palette_f(graph, f)
    max_f = max(f.values())
    if palette < max_f:
        raise ValueError(f"palette ({palette}) must be >= max f ({max_f})")

    from pysat.solvers import Minisat22

    list_sizes = [f[v] for v in range(n)]
    cnf, var = _cardinality_clauses(n, palette, list_sizes, symmetry)
    with Minisat22(bootstrap_with=cnf) as solver:
        while solver.solve():
            model = set(solver.get_model())
            lists = [{c for c in range(palette) if var(v, c) in model} for v in range(n)]
            coloring = find_list_coloring(graph, lists)
            if coloring is None:
                return lists
            solver.add_clause([-var(v, coloring[v]) for v in range(n)])
    return None


def find_bad_list(
    graph: Graph, k: int = DEFAULT_K, *, palette: int | None = None, symmetry: bool = True
) -> list[set[int]] | None:
    """A k-list assignment G cannot be colored from, or None if none exists.

    palette defaults to k*n (complete). A returned list is an independently
    re-checkable certificate; None means no bad list up to `palette` colors.
    """
    n = graph.n
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    if n == 0:
        return None
    return find_bad_list_f(
        graph, {v: k for v in range(n)}, palette=palette, symmetry=symmetry
    )


def verify_bad_list(graph: Graph, lists: list[set[int]], k: int) -> bool:
    """Re-check a certificate from scratch, independent of the SAT search:
    every list has size k and G genuinely has no coloring from `lists`."""
    return verify_bad_list_f(graph, lists, {v: k for v in range(graph.n)})


def verify_bad_list_f(graph: Graph, lists: list[set[int]], f: dict[int, int]) -> bool:
    """Re-check an f-list certificate: sizes match f and G has no coloring."""
    if len(lists) != graph.n:
        return False
    if any(len(s) != f[v] for v, s in enumerate(lists)):
        return False
    return find_list_coloring(graph, [set(s) for s in lists]) is None


def is_k_choosable_cegar(
    graph: Graph, k: int = DEFAULT_K, *, palette: int | None = None, symmetry: bool = True
) -> bool:
    """k-choosability via CEGAR. Complete when palette >= k*n (the default)."""
    return find_bad_list(graph, k, palette=palette, symmetry=symmetry) is None


def is_available() -> bool:
    """True iff the python-sat backend needed by the CEGAR search is importable."""
    try:
        import pysat  # noqa: F401
    except ImportError:
        return False
    return True
