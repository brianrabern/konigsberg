"""Empirical-tier tools. Trust roots: ENUMERATION, SOLVER, or CERTIFICATE.

Note the deliberate split (see ledger.TrustRoot):
  * solvers that merely ASSERT a result -> mint_solver_result (SOLVER)
  * solvers that emit a re-checkable certificate we independently verify
    -> mint_certificate (CERTIFICATE)  <- strictly stronger; prefer this.
"""
from __future__ import annotations

from konigsberg_empirical.coloring import alon_tarsi as _at
from konigsberg_empirical.coloring import choosability as _ch
from konigsberg_empirical.coloring import fixer_breaker as _fb
from konigsberg_empirical.search import counterexample as _cx
from konigsberg_empirical.search.enumerate import parse_graph6

from ..ledger import Claim, mint_certificate, mint_enumeration, mint_solver_result


def counterexample_search(predicate, bound: int) -> Claim | None:
    """Highest-ROI tool: kills bad conjectures before formalization cost.

    Returns a conjecture-refuting Claim if a counterexample is found, else a
    positive ENUMERATION Claim ("no counterexample up to n<=bound")."""
    witness = _cx.first_violation(predicate, bound)
    stmt = f"predicate holds for all graphs n<={bound}"
    if witness is not None:
        return mint_enumeration(f"COUNTEREXAMPLE to: {stmt} -> {witness}", bound=f"n<={bound}", exhaustive=True, tool="counterexample_search")
    return mint_enumeration(stmt, bound=f"n<={bound}", exhaustive=True, tool="counterexample_search")


def choosability_refute(graph6: str, k: int = 3, palette: int | None = None) -> Claim:
    """Search for a certificate that G (given as a graph6 string) is NOT k-choosable.

    Agent-callable: all args are JSON-native. On a hit, the bad list is re-verified
    by independent backtracking before the ledger accepts it -> certificate-checked.
    On a miss, mints a python-checked Claim ("no bad list up to the palette");
    with the default palette k*n this is a complete decision (=> k-choosable).
    """
    from .errors import ToolUnavailable

    if not _ch.is_available():
        raise ToolUnavailable("choosability_refute", "pysat not installed")
    graph = parse_graph6(graph6)
    bad = _ch.find_bad_list(graph, k, palette=palette)
    if bad is not None:
        if not _ch.verify_bad_list(graph, bad, k):  # defensive; must not happen
            raise ValueError("CEGAR returned a non-certificate")
        witness = [sorted(s) for s in bad]
        return mint_certificate(
            f"{graph6} is NOT {k}-choosable (bad list {witness})",
            checker="choosability.verify_bad_list",
            tool="choosability_refute",
        )
    pal = _ch.complete_palette(graph, k) if palette is None else palette
    complete = pal >= _ch.complete_palette(graph, k)
    verdict = f" => {k}-choosable" if complete else ""
    return mint_enumeration(
        f"{graph6}: no bad {k}-list up to palette {pal}{verdict}",
        bound=f"palette<={pal}",
        exhaustive=complete,
        tool="choosability_refute",
    )


def alon_tarsi(graph6: str) -> Claim:
    """Sufficient list-colorability via Alon–Tarsi. Agent-callable (graph6).

    A hit emits a re-checked orientation certificate → certificate-checked.
    A miss proves nothing about choosability (AT is sufficient only) and is
    stamped solver-certified with an honest "no verified certificate" statement.
    """
    graph = parse_graph6(graph6)
    cert = _at.certificate(graph)  # re-checkable orientation-difference object
    if cert is not None and _at.verify_certificate(graph, cert):
        return mint_certificate(
            f"{graph6} is Alon-Tarsi list-colorable "
            f"(AT certificate: even={cert.even}, odd={cert.odd})",
            checker="alon_tarsi.verify_certificate",
            tool="alon_tarsi",
        )
    return mint_solver_result(
        f"{graph6}: Alon-Tarsi (no verified certificate)",
        tool="alon_tarsi",
    )


def fixer_breaker(graph6: str, list_sizes: list[int]) -> Claim:
    """Online/paintability via FixerBreaker. Agent-callable (graph6 + list sizes).

    Until a winning-strategy certificate path lands (B4), results are
    solver-certified (port validated against MindTests fingerprints).
    """
    graph = parse_graph6(graph6)
    result = _fb.solve(graph, list_sizes)
    return mint_solver_result(
        f"{graph6}: fixer-breaker {'fixer wins' if result else 'breaker wins'} "
        f"(list sizes {list_sizes})",
        tool="fixer_breaker",
    )


def decide_colorable(graph6: str, k: int) -> Claim:
    """Decide ordinary proper k-colorability of a graph6 string.

    Colorable: return a witness coloring (re-checked) → certificate-checked Claim.
    The agent can pass that witness to `verify_coloring` to upgrade to proved.
    Not colorable: mint a not-k-colorable Claim — certificate-checked when a
    standard obstruction (clique K_{k+1}, or odd cycle for k=2) is extracted and
    re-verified; otherwise python-checked at the completeness of the SAT /
    backtracking decision. Ordinary chromatic colorability only — not choosability.
    """
    from konigsberg_empirical.coloring import list_checks as lc
    from konigsberg_empirical.search import sat

    graph = parse_graph6(graph6)
    if sat.is_available():
        coloring = sat.sat_find_k_coloring(graph, k)
    else:
        coloring = lc.find_k_coloring(graph, k)

    if coloring is not None:
        if not lc.is_proper_coloring(graph, coloring, k=k):
            raise ValueError("solver returned a non-proper coloring")
        return mint_certificate(
            f"{graph6} is {k}-colorable (witness coloring {list(coloring)})",
            checker="list_checks.is_proper_coloring",
            tool="decide_colorable",
        )

    obs = lc.find_noncolorability_obstruction(graph, k)
    if obs is not None:
        kind, verts = obs
        if kind == "clique":
            detail = f"clique K_{k + 1} on {verts}"
            checker = "list_checks.verify_clique"
        else:
            detail = f"odd cycle {verts}"
            checker = "list_checks.verify_odd_cycle"
        return mint_certificate(
            f"{graph6} is NOT {k}-colorable (obstruction: {detail})",
            checker=checker,
            tool="decide_colorable",
        )

    backend = "SAT" if sat.is_available() else "backtracking"
    return mint_enumeration(
        f"{graph6} is NOT {k}-colorable "
        f"(complete {k}-colorability decision via {backend})",
        bound=f"{backend} n={graph.n} k={k}",
        exhaustive=True,
        tool="decide_colorable",
    )
