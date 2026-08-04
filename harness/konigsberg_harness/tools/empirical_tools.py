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


def alon_tarsi(graph) -> Claim:
    cert = _at.certificate(graph)  # re-checkable orientation-difference object
    if cert is not None and _at.verify_certificate(graph, cert):
        return mint_certificate("Alon-Tarsi list-colorable", checker="alon_tarsi.verify_certificate", tool="alon_tarsi")
    return mint_solver_result("Alon-Tarsi (no verified certificate)", tool="alon_tarsi")


def fixer_breaker(graph, list_sizes) -> Claim:
    """The differentiator: fixer-breaker game solver for online/list choosability."""
    result = _fb.solve(graph, list_sizes)
    # TODO: emit + verify a winning-strategy certificate -> upgrade to mint_certificate.
    return mint_solver_result(f"fixer-breaker: {result}", tool="fixer_breaker")
