"""Empirical-tier tools. Trust roots: ENUMERATION, SOLVER, or CERTIFICATE.

Note the deliberate split (see ledger.TrustRoot):
  * solvers that merely ASSERT a result -> mint_solver_result (SOLVER)
  * solvers that emit a re-checkable certificate we independently verify
    -> mint_certificate (CERTIFICATE)  <- strictly stronger; prefer this.
"""
from __future__ import annotations

import os
import signal
from contextlib import contextmanager
from dataclasses import dataclass

from konigsberg_empirical import discharging as _dis
from konigsberg_empirical import reduction as _red
from konigsberg_empirical.coloring import alon_tarsi as _at
from konigsberg_empirical.coloring import choosability as _ch
from konigsberg_empirical.coloring import fixer_breaker as _fb
from konigsberg_empirical.search import counterexample as _cx
from konigsberg_empirical.search.enumerate import parse_graph6
from konigsberg_empirical.sufficient_only import assert_sufficient_only

from ..ledger import Claim, mint_certificate, mint_enumeration, mint_solver_result

# Live-hunt caps: f-choosability is Π₂-hard; n=9 (H??F~~~) hung the forever loop.
# Set KONIGSBERG_CHOOSABILITY_MAX_N=0 or TIMEOUT=0 to disable.
_DEFAULT_CHOOSABILITY_MAX_N = 6
_DEFAULT_CHOOSABILITY_TIMEOUT_S = 45.0


def _env_number(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    return float(raw)


def choosability_max_n() -> int:
    return int(_env_number("KONIGSBERG_CHOOSABILITY_MAX_N", _DEFAULT_CHOOSABILITY_MAX_N))


def choosability_timeout_s() -> float:
    return _env_number("KONIGSBERG_CHOOSABILITY_TIMEOUT", _DEFAULT_CHOOSABILITY_TIMEOUT_S)


def _guard_choosability_n(tool: str, n: int) -> None:
    from .errors import ToolBudgetExceeded

    cap = choosability_max_n()
    if cap > 0 and n > cap:
        raise ToolBudgetExceeded(
            tool,
            f"n={n} exceeds live cap {cap} (Π₂-hard SAT). "
            "Do not SAT-search listed cores / H??F~~~ / K₃∨Ē₆ — they are already "
            f"on 𝒞. Opt in with KONIGSBERG_CHOOSABILITY_MAX_N=0 (or a higher cap).",
        )


@contextmanager
def choosability_deadline(tool: str):
    """Wall-clock cap around a Π₂ choosability search (SIGALRM)."""
    from .errors import ToolBudgetExceeded

    timeout = choosability_timeout_s()
    if timeout <= 0 or not hasattr(signal, "SIGALRM") or not hasattr(signal, "setitimer"):
        yield
        return

    class _Deadline(Exception):
        pass

    def _handler(_signum, _frame):
        raise _Deadline()

    prev = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, _handler)
    signal.setitimer(signal.ITIMER_REAL, timeout)
    try:
        yield
    except _Deadline as exc:
        raise ToolBudgetExceeded(
            tool,
            f"timed out after {timeout:g}s (Π₂ search). Do not retry the same "
            f"graph; take discharging or a new n≤{choosability_max_n()} core.",
        ) from exc
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.0)
        signal.signal(signal.SIGALRM, prev)


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
    _guard_choosability_n("choosability_refute", graph.n)
    with choosability_deadline("choosability_refute"):
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


@dataclass(frozen=True)
class ReducibleConfigurationResult:
    """Non-Claim tool outcome: inconclusive or out-of-scope (sufficient-only)."""

    message: str
    out_of_scope: bool = False

    def __str__(self) -> str:
        return self.message


def _normalize_degrees(
    degrees: dict[str, int] | list[int], n: int
) -> dict[int, int]:
    if isinstance(degrees, list):
        if len(degrees) != n:
            raise ValueError(f"expected {n} degrees, got {len(degrees)}")
        return {v: int(d) for v, d in enumerate(degrees)}
    spec = {int(k): int(v) for k, v in degrees.items()}
    if set(spec) != set(range(n)):
        raise ValueError(f"degrees must cover vertices 0..{n - 1}")
    return spec


def reducible_configuration(
    core: str,
    degrees: dict[str, int] | list[int],
    D: int | None = None,
) -> Claim | ReducibleConfigurationResult:
    """Test whether a local configuration is reducible in a minimal BK counterexample.

    Standing hypotheses H_BK: Δ=D≥9, K_D-free, D-critical. Builds
    f(v) = (D-1) - d_G(v) + deg_K(v) from the degree spec (never model-supplied),
    then tests f-choosability of the core via the choosability solver.

    f-choosability of the core is SUFFICIENT for reducibility, not necessary — a
    miss proves nothing, exactly like alon_tarsi. The forbidden-configuration
    conclusion names H_BK. The reducibility bridge lemma
    BK.reducible_of_fChoosable is formalized in Literature; HITs drop the
    conditional tag when that status is ``formalized`` (fail-closed: any other
    status keeps the tag).

    HIT  → core is f-choosable ⇒ configuration FORBIDDEN in every minimal
           counterexample (enumeration-rooted). SUFFICIENT ONLY.
    MISS → method inconclusive; mints no Claim and proves nothing.
    """
    from .errors import ToolBudgetExceeded, ToolUnavailable

    if not _ch.is_available():
        raise ToolUnavailable("reducible_configuration", "pysat not installed")

    graph = parse_graph6(core)
    _guard_choosability_n("reducible_configuration", graph.n)
    degree_spec = _normalize_degrees(degrees, graph.n)
    try:
        config = _red.build_configuration(graph, degree_spec, D)
        with choosability_deadline("reducible_configuration"):
            result = _red.reducible(config)
    except _red.ToolBudgetExceeded as e:
        raise ToolBudgetExceeded("reducible_configuration", str(e)) from e

    if result.out_of_scope:
        return ReducibleConfigurationResult(
            assert_sufficient_only(f"inconclusive (out of scope): {result.reason}"),
            out_of_scope=True,
        )
    if not result.hit:
        witness = (
            [sorted(s) for s in result.bad_list] if result.bad_list is not None else None
        )
        extra = f"; witness bad f-list {witness}" if witness is not None else ""
        return ReducibleConfigurationResult(
            assert_sufficient_only(
                f"inconclusive: {result.reason}{extra} (proves nothing about reducibility)"
            )
        )

    stmt = _red.forbidden_configuration_statement(
        core, config, palette=result.palette
    )
    return mint_enumeration(
        stmt,
        bound=f"palette<={result.palette}",
        exhaustive=True,
        tool="reducible_configuration",
    )


@dataclass
class DischargingResult:
    """Non-Claim tool outcome: argument does not close (sufficient-only)."""

    message: str
    survivors: tuple[str, ...] = ()

    def __str__(self) -> str:
        return self.message


def discharging_unavoidable(
    bind,
    D: int,
    mu: dict[str, int],
    rules: list[dict],
    forbidden: list[str],
) -> Claim | DischargingResult:
    """Verify a proposed discharging argument at Δ = D (v1: D = 9 only).

    The model/human proposes μ and the transfer rules; the engine checks
    conservation, the global charge sign, and every radius-1 neighborhood
    type. UNAVOIDABLE is SUFFICIENT only — a miss returns the surviving
    neighborhood types and proves nothing.

    Forbidden cores must already be minted reducible on the ledger.
    The UNAVOIDABLE conclusion is conditional on
    BK.reducible_and_unavoidable_imp_no_counterexample until that
    closure lemma is kernel-proved.
    """
    from ..campaign import forbidden_cores
    from .errors import ToolBudgetExceeded

    claims = bind.ledger.claims() if bind is not None and bind.ledger is not None else ()
    reducible = set(forbidden_cores(claims))
    arg = _dis.build_argument(D, mu, rules, forbidden)
    try:
        result = _dis.verify_unavoidable(arg, reducible_cores=reducible)
    except _dis.ToolBudgetExceeded as e:
        raise ToolBudgetExceeded("discharging_unavoidable", str(e)) from e
    except _dis.DischargeRejected as e:
        if bind is not None:
            bind.last_discharge_note = str(e)
            bind.last_discharge_survivors = ()
        raise ValueError(str(e)) from e

    if not result.hit:
        if bind is not None:
            bind.last_discharge_survivors = result.survivors
            bind.last_discharge_note = result.reason
        return DischargingResult(
            assert_sufficient_only(result.reason), survivors=result.survivors
        )

    if bind is not None:
        bind.last_discharge_survivors = ()
        bind.last_discharge_note = ""
    stmt = _dis.unavoidable_statement(arg, result)
    n_types = len(_dis.local_types(arg.D))
    return mint_enumeration(
        stmt,
        bound=f"D={arg.D} local-types={n_types}",
        exhaustive=True,
        tool="discharging_unavoidable",
    )


def discharging_cover(
    bind,
    center_deg: int,
    n_high: int,
    n_low: int | None = None,
) -> str:
    """Catalog cover of a v1 local type via ``core_forced_in_type``.

    Does not mint a Claim. Unminted hits are hints for
    ``reducible_configuration``; only ledger cores may enter 𝒞.
    """
    from ..campaign import forbidden_cores

    if n_low is None:
        n_low = int(center_deg) - int(n_high)
    if int(n_high) + int(n_low) != int(center_deg):
        raise ValueError(
            f"n_high+n_low must equal center_deg (got {n_high}+{n_low} vs {center_deg})"
        )
    typ = _dis.LocalType(int(center_deg), int(n_high), int(n_low))
    claims = bind.ledger.claims() if bind is not None and bind.ledger is not None else ()
    minted = set(forbidden_cores(claims))
    cover = _dis.cover_type(typ, _dis.load_rabern_catalog(), minted=minted)
    return _dis.describe_cover(cover, typ)


def discharging_search(
    bind,
    D: int,
    mu: dict[str, int],
    rules: list[dict],
    forbidden: list[str] | None = None,
    max_iters: int = 12,
) -> Claim | DischargingResult:
    """Cover survivors from the minted catalog, then mutate μ/rules.

    CLOSED mints the same UNAVOIDABLE Claim as ``discharging_unavoidable``.
    STUCK with a residual mints an irreducible-frontier Claim (not a
    forbidden configuration). A miss proves nothing.
    """
    from ..campaign import forbidden_cores
    from .errors import ToolBudgetExceeded

    claims = bind.ledger.claims() if bind is not None and bind.ledger is not None else ()
    reducible = set(forbidden_cores(claims))
    cores = list(forbidden) if forbidden is not None else list(reducible)
    try:
        outcome = _dis.run_search(
            D=D,
            mu=mu,
            rules=rules,
            forbidden=cores,
            reducible_cores=reducible,
            max_iters=max_iters,
        )
    except _dis.ToolBudgetExceeded as e:
        raise ToolBudgetExceeded("discharging_search", str(e)) from e
    except _dis.DischargeRejected as e:
        if bind is not None:
            bind.last_discharge_note = str(e)
            bind.last_discharge_survivors = ()
            bind.last_search_banner = ""
        raise ValueError(str(e)) from e

    banner = _dis.format_search_banner(outcome)
    if bind is not None:
        bind.last_search_banner = banner
        bind.last_discharge_note = outcome.result.reason
        bind.last_discharge_survivors = (
            () if outcome.result.hit else outcome.result.survivors
        )

    if outcome.status == "CLOSED":
        arg = _dis.build_argument(D, outcome.mu, list(outcome.rules), list(outcome.forbidden))
        stmt = _dis.unavoidable_statement(arg, outcome.result)
        n_types = len(_dis.local_types(arg.D))
        return mint_enumeration(
            stmt,
            bound=f"D={arg.D} local-types={n_types} search-iters={outcome.iterations}",
            exhaustive=True,
            tool="discharging_search",
        )

    if not outcome.result.ranked:
        return DischargingResult(
            assert_sufficient_only(f"{banner} {outcome.result.reason}"),
            survivors=outcome.result.survivors,
        )

    return mint_enumeration(
        _dis.frontier_statement(outcome),
        bound=f"residual={len(outcome.result.ranked)} iters={outcome.iterations}",
        exhaustive=False,
        tool="discharging_search",
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


def reed_predicate(graph6: str, *, repl=None) -> Claim | list[Claim]:
    """Evaluate Reed's conjecture on one graph.

    Reed's conjecture (open): χ(G) ≤ ⌈(Δ(G) + ω(G) + 1)/2⌉ for every graph G.
    Unlike BK there is no degree hypothesis — every graph is in scope. Returns
    satisfies / VIOLATES, carrying Δ/ω/χ certificates, and flags the tight case
    (χ = the bound) — the interesting extremal data. A violation is maximally
    certified and, when a Lean REPL is bound, the χ-coloring is kernel-upgraded
    via verify_coloring. Ordinary chromatic Reed — not the fractional/local forms.

    Bound arithmetic: ⌈(Δ+ω+1)/2⌉ = (Δ+ω+2)//2. Tight for cliques and odd cycles
    (e.g. K_n, C_5, and the Petersen graph).
    """
    from konigsberg_empirical.coloring import list_checks as lc

    graph = parse_graph6(graph6)
    deg = [graph.degree(v) for v in range(graph.n)]
    delta = max(deg) if deg else 0

    certs = lc.chromatic_certificates(graph)
    if not lc.verify_chromatic_bundle(graph, certs):
        raise ValueError("Reed certificate bundle failed independent check")
    bound = (delta + certs.omega + 2) // 2  # ⌈(Δ+ω+1)/2⌉
    tight = certs.chi == bound
    tight_note = (
        "Tight (χ equals the bound)."
        if tight
        else f"Slack {bound - certs.chi} below the bound."
    )
    bundle = (
        f"Δ={delta}, ω={certs.omega}, χ={certs.chi}, "
        f"⌈(Δ+ω+1)/2⌉={bound}; degrees {deg}; "
        f"clique {certs.clique}; χ-coloring {certs.coloring}; "
        f"not {max(certs.chi - 1, 0)}-colorable: {certs.lower_detail}"
    )

    if certs.chi <= bound:
        return mint_certificate(
            f"{graph6} satisfies Reed ({bundle}). {tight_note}",
            checker="list_checks.verify_chromatic_bundle",
            tool="reed_predicate",
        )

    # Violation — a counterexample to a famous open conjecture; maximally certified.
    main = mint_certificate(
        f"{graph6} VIOLATES Reed ({bundle}).",
        checker="list_checks.verify_chromatic_bundle",
        tool="reed_predicate",
    )
    if repl is None:
        return main

    from .bridge import verify_coloring

    proved = verify_coloring(graph6, certs.coloring, repl=repl)
    return [main, proved]


def reed_sweep(
    n_min: int = 2,
    n_max: int = 7,
    connected: bool = True,
    max_tight: int = 30,
) -> Claim:
    """Census: verify Reed's bound over all graphs on n_min..n_max vertices in ONE
    pass, cataloguing the tight cases.

    Reed: χ(G) ≤ ⌈(Δ+ω+1)/2⌉ = (Δ+ω+2)//2. This runs the reed_predicate check
    in-process on each enumerated graph — no agent round-trips — and mints a single
    summary Claim: how many graphs were checked, whether all satisfy Reed, the
    tight-case census (χ = the bound), and the first violation with its full Δ/ω/χ
    certificate if one is found. This is the right granularity for a census; do NOT
    loop reed_predicate by hand over an enumeration.

    Enumeration is geng (or the atlas for n≤7); cap n_max accordingly. Since Reed
    is known to hold at small size, a reported violation here is far more likely a
    bug to investigate than a counterexample.
    """
    from konigsberg_empirical.coloring import choosability as ch
    from konigsberg_empirical.coloring import list_checks as lc
    from konigsberg_empirical.fundamentals.codec import to_graph6
    from konigsberg_empirical.search.enumerate import all_graphs

    from .errors import ToolUnavailable

    if not ch.is_available():
        raise ToolUnavailable("reed_sweep", "pysat not installed")
    if n_min < 1 or n_max < n_min:
        raise ValueError(f"bad n range: n_min={n_min}, n_max={n_max}")

    constraints = {"connected": True} if connected else None
    checked = 0
    tight_count = 0
    tight_examples: list[str] = []
    violation: str | None = None

    for n in range(n_min, n_max + 1):
        for g in all_graphs(n, constraints=constraints):
            deg = [g.degree(v) for v in range(g.n)]
            delta = max(deg) if deg else 0
            certs = lc.chromatic_certificates(g)
            if not lc.verify_chromatic_bundle(g, certs):
                raise ValueError("reed_sweep: chromatic bundle failed independent check")
            bound = (delta + certs.omega + 2) // 2  # ⌈(Δ+ω+1)/2⌉
            checked += 1
            if certs.chi > bound:
                violation = (
                    f"{to_graph6(g)}: Δ={delta}, ω={certs.omega}, χ={certs.chi} "
                    f"> ⌈(Δ+ω+1)/2⌉={bound}; χ-coloring {certs.coloring}; "
                    f"clique {certs.clique}"
                )
                break
            if certs.chi == bound:
                tight_count += 1
                if len(tight_examples) < max_tight:
                    tight_examples.append(
                        f"{to_graph6(g)}(Δ={delta},ω={certs.omega},χ={certs.chi})"
                    )
        if violation is not None:
            break

    family = "connected" if connected else "all"
    if violation is not None:
        return mint_certificate(
            f"reed_sweep n={n_min}..{n_max} ({family}): VIOLATION after {checked} "
            f"graphs — {violation}. (Reed holds at small size; investigate as a "
            "likely bug before treating as a counterexample.)",
            checker="list_checks.verify_chromatic_bundle",
            tool="reed_sweep",
        )
    extra = "" if tight_count <= len(tight_examples) else f" (+{tight_count - len(tight_examples)} more)"
    return mint_enumeration(
        f"reed_sweep n={n_min}..{n_max} ({family}): Reed's bound holds on all "
        f"{checked} graphs; {tight_count} tight (χ = bound): {tight_examples}{extra}",
        bound=f"n={n_min}..{n_max} {family}; checked={checked}",
        exhaustive=True,
        tool="reed_sweep",
    )


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


def list_critical_definition(m: int) -> str:
    """Harness-rendered Definition used: line for the Cranston–Rabern index."""
    return (
        f"{m}-list-critical = not {m - 1}-choosable, edge-minimal "
        f"[Cranston–Rabern; Lean KListCritical / EdgeKListCritical]"
    )


def list_critical(graph6: str, m: int, palette: int | None = None) -> Claim:
    """Decide whether G is m-list-critical (Cranston–Rabern index, baked in).

    Convention (also Lean ``KListCritical`` / ``EdgeKListCritical``): G is
    m-list-critical iff G is not (m−1)-choosable and every proper subgraph is
    (m−1)-choosable. This tool tests the **edge-critical** form — every G−e is
    (m−1)-choosable — the standard reduction for this critical family (so
    "proper subgraph" here means edge-minimality, not an exhaustive subgraph
    scan). Internally: ``is_choice_critical(G, m-1)``.

    Example: ``list_critical(K₄, 4)`` tests not-3-choosable + edge-minimal.
    Do **not** reassemble from ``choosability_refute`` with a guessed k — that
    is how the index gets silently wrong.

    Certificates: a re-checked bad (m−1)-list (certificate-checked) when G is
    not (m−1)-choosable; each G−e (m−1)-choosability decision at the default
    palette k·n is complete (else the palette caveat is stated). The verdict
    as a whole inherits that caveat on the minimality side.
    """
    from konigsberg_empirical.coloring import bk as _bk
    from konigsberg_empirical.coloring import choosability as ch

    from .errors import ToolUnavailable

    if not ch.is_available():
        raise ToolUnavailable("list_critical", "pysat not installed")
    if m < 2:
        raise ValueError(f"m-list-critical requires m≥2, got m={m}")

    graph = parse_graph6(graph6)
    k = m - 1  # choosability parameter — index baked in, not guessed
    pal = ch.complete_palette(graph, k) if palette is None else palette
    complete = pal >= ch.complete_palette(graph, k)
    index_note = (
        f"index=Cranston–Rabern (m-list-critical ↔ not (m−1)-choosable + "
        f"edge-minimal); tested via is_choice_critical(G, k={k})"
    )

    bad = ch.find_bad_list(graph, k, palette=palette)
    if bad is None:
        verdict = "choosable" if complete else f"no bad {k}-list up to palette {pal}"
        return mint_enumeration(
            f"{graph6} is NOT {m}-list-critical ({index_note}). "
            f"Reason: G is {k}-{verdict}.",
            bound=f"palette<={pal}",
            exhaustive=complete,
            tool="list_critical",
        )

    if not ch.verify_bad_list(graph, bad, k):
        raise ValueError("CEGAR returned a non-certificate for list_critical")
    witness = [sorted(s) for s in bad]

    failing_edge = None
    ok_edges: list[tuple[int, int]] = []
    for e in sorted(graph.edges):
        if ch.find_bad_list(_bk.without_edge(graph, e), k, palette=palette) is None:
            ok_edges.append(e)
        else:
            failing_edge = e
            break

    if failing_edge is not None:
        return mint_certificate(
            f"{graph6} is NOT {m}-list-critical ({index_note}). "
            f"Has bad {k}-list {witness} (certificate-checked) but "
            f"G-{list(failing_edge)} is also not {k}-choosable (not edge-minimal).",
            checker="choosability.verify_bad_list",
            tool="list_critical",
        )

    pal_note = (
        f"all {len(ok_edges)} edge deletions {k}-choosable at palette {pal} "
        + ("(complete decision)" if complete else "(palette caveat — not a complete decision)")
    )
    stmt = (
        f"{graph6} IS {m}-list-critical ({index_note}). "
        f"Bad {k}-list {witness} (certificate-checked); {pal_note}; "
        f"edges checked {ok_edges}."
    )
    if complete:
        return mint_certificate(
            stmt,
            checker="choosability.verify_bad_list",
            tool="list_critical",
        )
    return mint_enumeration(
        stmt,
        bound=f"palette<={pal}",
        exhaustive=False,
        tool="list_critical",
    )
