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


def max_degree(graph6: str) -> Claim:
    """Δ(G) with degree sequence. Trivial; python-checked."""
    graph = parse_graph6(graph6)
    deg = [graph.degree(v) for v in range(graph.n)]
    delta = max(deg) if deg else 0
    return mint_enumeration(
        f"{graph6} has Δ={delta} (degree sequence {deg})",
        bound=f"n={graph.n}",
        exhaustive=True,
        tool="max_degree",
    )


def clique_number(graph6: str) -> Claim:
    """ω(G) with a witnessing clique (re-checked) → certificate-checked."""
    from konigsberg_empirical.coloring import list_checks as lc

    graph = parse_graph6(graph6)
    omega, clique = lc.clique_number_witness(graph)
    if not lc.verify_clique(graph, clique) or len(clique) != omega:
        raise ValueError("clique witness failed independent check")
    return mint_certificate(
        f"{graph6} has ω={omega} (witnessing clique {list(clique)})",
        checker="list_checks.verify_clique",
        tool="clique_number",
    )


def chromatic_number(graph6: str) -> Claim:
    """χ(G): least k with a proper coloring, searching up from ω.

    Returns both certificates: a proper χ-coloring (upper — feed to
    verify_coloring for a kernel upgrade) and not-(χ−1) evidence (lower).
    certificate-checked when the bundle re-verifies.
    """
    from konigsberg_empirical.coloring import list_checks as lc

    graph = parse_graph6(graph6)
    certs = lc.chromatic_certificates(graph)
    if not lc.verify_chromatic_bundle(graph, certs):
        raise ValueError("chromatic certificate bundle failed independent check")

    stmt = (
        f"{graph6} has χ={certs.chi} "
        f"(χ-coloring {certs.coloring}; not {max(certs.chi - 1, 0)}-colorable: "
        f"{certs.lower_detail}; ω={certs.omega} clique {certs.clique})"
    )
    if certs.lower_kind in ("clique", "odd_cycle", "none") or (
        certs.lower_kind == "unsat" and certs.chi <= 1
    ):
        return mint_certificate(
            stmt,
            checker="list_checks.verify_chromatic_bundle",
            tool="chromatic_number",
        )
    # Lower bound rests on complete decision completeness (no extracted obstruction).
    return mint_enumeration(
        stmt + " [lower bound via complete decision]",
        bound=f"chromatic n={graph.n}",
        exhaustive=True,
        tool="chromatic_number",
    )


def bk_predicate(graph6: str, *, repl=None) -> Claim | list[Claim]:
    """Evaluate the Borodin–Kostochka conjecture on one graph.

    Hypothesis: Δ ≥ 9. Claim: χ ≤ max{ω, Δ−1}.
    Returns hypothesis-not-met / satisfies / VIOLATES, carrying Δ/ω/χ certificates.
    A violation is maximally certified (degree sequence, ω-clique, χ-coloring,
    not-(χ−1) evidence); when a Lean REPL is bound, the χ-coloring is also
    kernel-upgraded via verify_coloring. Ordinary chromatic BK only — not choosability.

    Honest note: a counterexample requires χ = Δ, ω ≤ Δ−1, Δ ≥ 9 (since
    χ ≤ Δ+1 and χ = Δ+1 forces K_{Δ+1} by Brooks) — the tight regime.
    """
    from konigsberg_empirical.coloring import list_checks as lc

    graph = parse_graph6(graph6)
    deg = [graph.degree(v) for v in range(graph.n)]
    delta = max(deg) if deg else 0

    if delta < 9:
        return mint_enumeration(
            f"{graph6}: BK hypothesis not met (Δ={delta} < 9; "
            f"graph irrelevant to the conjecture; degrees {deg})",
            bound=f"Δ={delta}",
            exhaustive=True,
            tool="bk_predicate",
        )

    certs = lc.chromatic_certificates(graph)
    if not lc.verify_chromatic_bundle(graph, certs):
        raise ValueError("BK certificate bundle failed independent check")
    bound = max(certs.omega, delta - 1)
    tight_note = (
        "Note: a counterexample requires χ=Δ, ω≤Δ−1, Δ≥9 "
        "(χ≤Δ+1 and χ=Δ+1 forces K_{Δ+1} by Brooks) — the tight regime."
    )
    bundle = (
        f"Δ={delta}, ω={certs.omega}, χ={certs.chi}, "
        f"max(ω,Δ−1)={bound}; degrees {deg}; "
        f"clique {certs.clique}; χ-coloring {certs.coloring}; "
        f"not {certs.chi - 1}-colorable: {certs.lower_detail}"
    )

    if certs.chi <= bound:
        return mint_certificate(
            f"{graph6} satisfies BK ({bundle}). {tight_note}",
            checker="list_checks.verify_chromatic_bundle",
            tool="bk_predicate",
        )

    # Violation — major; maximally certified.
    main = mint_certificate(
        f"{graph6} VIOLATES BK ({bundle}). {tight_note}",
        checker="list_checks.verify_chromatic_bundle",
        tool="bk_predicate",
    )
    if repl is None:
        return main

    from .bridge import verify_coloring

    proved = verify_coloring(graph6, certs.coloring, repl=repl)
    return [main, proved]


def bk_search(
    n_max: int,
    k: int = 3,
    n_min: int = 6,
    palette: int | None = None,
    max_hits: int = 5,
) -> Claim:
    """Principled Rabern-style BK candidate search (bad-K₂ / choice-critical).

    Family: connected graphs with degrees in {3,4}, enumerated via geng (or
    atlas for n≤7). Filters: bad-K₂ edge, K4-free, k-colorable, then
    choosability / edge-choice-criticality via find_bad_k2_critical.

    LIMITS: this is NOT a search over Δ≥9 chromatic-BK-tight graphs — those
    require ≥10 vertices and a degree-≥9 vertex. Hits here are choice-critical
    candidates in the deg-{3,4} family; evaluate chromatic BK with bk_predicate
    (which will reject Δ<9 as hypothesis-not-met). Prefer this over inventing
    graph6 strings.
    """
    from konigsberg_empirical.coloring import bk as _bk
    from konigsberg_empirical.coloring import choosability as ch
    from konigsberg_empirical.search.enumerate import all_graphs

    from .errors import ToolUnavailable

    if not ch.is_available():
        raise ToolUnavailable("bk_search", "pysat not installed")
    if n_min < 1 or n_max < n_min:
        raise ValueError(f"bad n range: n_min={n_min}, n_max={n_max}")
    if max_hits < 1:
        raise ValueError("max_hits must be ≥1")

    hits: list[dict] = []
    scanned = 0
    for n in range(n_min, n_max + 1):
        for hit in _bk.find_bad_k2_critical(
            all_graphs(n, constraints=_bk.BK_SEARCH_CONSTRAINTS),
            k=k,
            palette=palette,
        ):
            scanned += 1
            g = hit["graph"]
            hits.append(
                {
                    "n": n,
                    "graph6": _bk.to_graph6(g),
                    "bad_k2_edges": hit["bad_k2_edges"],
                    "bad_list": hit["bad_list"],
                    "critical": hit["critical"],
                }
            )
            if len(hits) >= max_hits:
                break
        if len(hits) >= max_hits:
            break

    pal = palette if palette is not None else "k*n (complete)"
    limits = (
        "LIMITS: family=connected deg∈{3,4}; filters=bad-K2,K4-free,k-colorable,"
        "choice-criticality — not a Δ≥9 chromatic BK search"
    )
    if not hits:
        stmt = (
            f"bk_search n={n_min}..{n_max} k={k} palette={pal}: no hits. {limits}"
        )
    else:
        stmt = (
            f"bk_search n={n_min}..{n_max} k={k} palette={pal}: "
            f"{len(hits)} hit(s) {hits}. {limits}"
        )
    complete = palette is None
    return mint_enumeration(
        stmt,
        bound=f"n={n_min}..{n_max} deg∈{{3,4}} scanned_hits={scanned}",
        exhaustive=complete,
        tool="bk_search",
    )
