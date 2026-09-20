"""Discharging verifier for BK at Δ = 9 (v1).

The tool verifies a proposed (μ, rules, 𝒞) argument. It does not invent one.
UNAVOIDABLE is sufficient-only: a MISS returns surviving neighborhood types
and mints nothing. A miss proves nothing.

v1 local types are closed-neighborhood *degree signatures*
(center degree ∈ {8,9}, counts of deg-8 / deg-9 neighbors). That is the
finite 1-hop world of a 9-critical graph. Radius > 1 is a budget error.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core import Graph
from ..search.enumerate import parse_graph6
from ..sufficient_only import assert_sufficient_only

V1_D = 9
MAX_RADIUS = 1
MAX_FORBIDDEN = 64
CLOSURE_LEMMA = "BK.reducible_and_unavoidable_imp_no_counterexample"
CLOSURE_TAG = f"[conditional on discharging closure lemma {CLOSURE_LEMMA}]"

_LOW_PATTERNS = frozenset({"low", "deg8", "d-1", "dminus1"})
_HIGH_PATTERNS = frozenset({"high", "deg9", "d", "delta"})
_ANY_PATTERNS = frozenset({"any", "all", "*"})
_TRANSFER_PATTERNS = _LOW_PATTERNS | _HIGH_PATTERNS | _ANY_PATTERNS


class ToolBudgetExceeded(ValueError):
    """Raised when a discharging argument exceeds v1 enumeration bounds."""


class DischargeRejected(ValueError):
    """Invalid argument (non-conserving rules, wrong D, ledger coupling)."""


@dataclass(frozen=True)
class Charge:
    """Initial charge μ(v) as a function of degree."""

    mu: dict[int, int]


@dataclass(frozen=True)
class Rule:
    """Transfer ``amount`` from vertices of ``from_deg`` to matching neighbors."""

    from_deg: int
    to_pattern: str
    amount: int
    radius: int = 1


@dataclass(frozen=True)
class DischargingArgument:
    D: int
    charge: Charge
    rules: tuple[Rule, ...]
    forbidden: tuple[str, ...]


@dataclass(frozen=True)
class LocalType:
    """Closed neighborhood degree signature at Δ = D."""

    center_deg: int
    n_high: int
    n_low: int

    def label(self) -> str:
        return f"deg{self.center_deg}(high={self.n_high},low={self.n_low})"


@dataclass(frozen=True)
class Survivor:
    """One local type that neither contains 𝒞 nor meets the charge bound."""

    typ: LocalType
    charge: int
    deficit: int
    reason: str = "charge-infeasible"

    def label(self) -> str:
        return (
            f"{self.typ.label()} final={self.charge} deficit={self.deficit}"
        )


@dataclass(frozen=True)
class DischargeResult:
    hit: bool
    reason: str
    survivors: tuple[str, ...] = ()
    ranked: tuple[Survivor, ...] = ()
    checked: int = 0
    global_sign: int | None = None
    intended_sign: int | None = None
    rejected: bool = False

    @property
    def total_deficit(self) -> int:
        return sum(s.deficit for s in self.ranked)


def _coerce_mu(mu: dict) -> dict[int, int]:
    return {int(k): int(v) for k, v in mu.items()}


def build_argument(
    D: int,
    mu: dict,
    rules: list | tuple,
    forbidden: list[str] | tuple[str, ...],
) -> DischargingArgument:
    """Assemble a DischargingArgument; derive nothing the model should not supply."""
    parsed_rules: list[Rule] = []
    for raw in rules:
        if isinstance(raw, Rule):
            parsed_rules.append(raw)
            continue
        parsed_rules.append(
            Rule(
                from_deg=int(raw["from_deg"]),
                to_pattern=str(raw["to_pattern"]),
                amount=int(raw["amount"]),
                radius=int(raw.get("radius", 1)),
            )
        )
    return DischargingArgument(
        D=int(D),
        charge=Charge(_coerce_mu(mu)),
        rules=tuple(parsed_rules),
        forbidden=tuple(str(c) for c in forbidden),
    )


def local_types(D: int) -> tuple[LocalType, ...]:
    types: list[LocalType] = []
    for d in (D - 1, D):
        for n_high in range(d + 1):
            types.append(LocalType(center_deg=d, n_high=n_high, n_low=d - n_high))
    return tuple(types)


def _n_matching(typ: LocalType, pattern: str) -> int:
    p = pattern.lower()
    if p in _LOW_PATTERNS:
        return typ.n_low
    if p in _HIGH_PATTERNS:
        return typ.n_high
    if p in _ANY_PATTERNS:
        return typ.center_deg
    return 0


def _pattern_matches_deg(pattern: str, deg: int, D: int) -> bool:
    p = pattern.lower()
    if p in _ANY_PATTERNS:
        return True
    if p in _LOW_PATTERNS:
        return deg == D - 1
    if p in _HIGH_PATTERNS:
        return deg == D
    return False


def _has_dominating_vertex(graph: Graph) -> bool:
    if graph.n <= 1:
        return True
    return any(graph.degree(v) == graph.n - 1 for v in range(graph.n))


def core_forced_in_type(core: Graph, typ: LocalType) -> bool:
    """True when every closed neighborhood of this signature contains ``core``.

    v1: an edge is forced whenever the center has a neighbor; a core that *is*
    a closed neighborhood (dominating vertex, order = 1 + center_deg) is forced
    for that center degree. Other cores are not forced by the signature alone.
    """
    if core.n <= 1:
        return True
    if core.n == 2 and len(core.edges) == 1:
        return typ.center_deg >= 1
    return _has_dominating_vertex(core) and core.n == typ.center_deg + 1


def _check_conservation(arg: DischargingArgument) -> None:
    mu = arg.charge.mu
    allowed_degs = {arg.D - 1, arg.D}
    for rule in arg.rules:
        if rule.radius > MAX_RADIUS:
            raise ToolBudgetExceeded(
                f"rule radius {rule.radius} exceeds v1 cap {MAX_RADIUS}"
            )
        if rule.radius < 1:
            raise DischargeRejected(
                "non-conserving rule: radius must be a neighbor transfer "
                f"(got {rule.radius})"
            )
        if rule.amount <= 0:
            raise DischargeRejected(
                "non-conserving rule: amount must be a positive transfer "
                f"(got {rule.amount})"
            )
        if rule.to_pattern.lower() not in _TRANSFER_PATTERNS:
            raise DischargeRejected(
                f"non-conserving rule: to_pattern {rule.to_pattern!r} is not a "
                "neighbor transfer (send = receive)"
            )
        if rule.from_deg not in allowed_degs or rule.from_deg not in mu:
            raise DischargeRejected(
                f"non-conserving rule: from_deg {rule.from_deg} is not a "
                f"live degree in {{D-1, D}} with a μ entry"
            )


def global_sign(mu: dict[int, int], D: int) -> int | None:
    """Forced sign of Σμ on a Δ=D graph with δ≥D−1, or None if unforced.

    A Δ=D graph has at least one degree-D vertex, so μ(D)>0 and μ(D−1)≥0
    forces Σμ ≥ μ(D) > 0 (and the negative twin). Mixed signs and a zero
    at D with the opposite sign at D−1 remain unforced.
    """
    low, high = mu.get(D - 1), mu.get(D)
    if low is None or high is None:
        raise DischargeRejected(f"μ must specify degrees {D - 1} and {D}")
    if high > 0 and low >= 0:
        return 1
    if high < 0 and low <= 0:
        return -1
    return None


def intended_sign(mu: dict[int, int], D: int) -> int | None:
    """Sign used to rank local residuals when Σμ may still be unforced.

    HIT still requires ``global_sign``; this only scores which types miss
    the charge bound so mixed μ can produce a gradient.
    """
    forced = global_sign(mu, D)
    if forced is not None:
        return forced
    low, high = mu[D - 1], mu[D]
    if high != 0:
        return 1 if high > 0 else -1
    if low != 0:
        return 1 if low > 0 else -1
    return None


def _deficit(charge: int, sign: int) -> int:
    """How far ``charge`` is from the feasible side of ``sign``."""
    if sign < 0:
        return max(0, -charge)
    return max(0, charge)


def final_charge(typ: LocalType, arg: DischargingArgument) -> int:
    q = arg.charge.mu[typ.center_deg]
    D = arg.D
    for rule in arg.rules:
        if rule.from_deg == typ.center_deg:
            q -= rule.amount * _n_matching(typ, rule.to_pattern)
        if _pattern_matches_deg(rule.to_pattern, typ.center_deg, D):
            if rule.from_deg == D - 1:
                senders = typ.n_low
            elif rule.from_deg == D:
                senders = typ.n_high
            else:
                senders = 0
            q += rule.amount * senders
    return q


def verify_unavoidable(
    arg: DischargingArgument,
    *,
    reducible_cores: set[str] | frozenset[str],
) -> DischargeResult:
    """Verify unavoidability of ``arg.forbidden`` under μ and rules.

    HIT  — every surviving type meets the charge bound while global Σμ has
           the opposite sign ⇒ 𝒞 is UNAVOIDABLE (sufficient-only).
    MISS — a neighborhood type survives with the wrong sign; proves nothing.
           Ranked residuals are still returned when Σμ is unforced so a
           search can use them as a gradient (that miss still cannot HIT).
    """
    if arg.D != V1_D:
        raise DischargeRejected(f"v1 is D={V1_D} only (got D={arg.D})")
    if len(arg.forbidden) > MAX_FORBIDDEN:
        raise ToolBudgetExceeded(
            f"{len(arg.forbidden)} forbidden cores exceeds cap {MAX_FORBIDDEN}"
        )
    missing = [c for c in arg.forbidden if c not in reducible_cores]
    if missing:
        raise DischargeRejected(
            "ledger coupling: forbidden cores not minted reducible: "
            + ", ".join(missing)
        )
    _check_conservation(arg)
    gsign = global_sign(arg.charge.mu, arg.D)
    isign = intended_sign(arg.charge.mu, arg.D)
    cores = [parse_graph6(g6) for g6 in arg.forbidden]
    types = local_types(arg.D)
    ranked: list[Survivor] = []
    for typ in types:
        if any(core_forced_in_type(core, typ) for core in cores):
            continue
        if isign is None:
            continue
        q = final_charge(typ, arg)
        deficit = _deficit(q, isign)
        if deficit > 0:
            ranked.append(
                Survivor(
                    typ=typ,
                    charge=q,
                    deficit=deficit,
                    reason="charge-infeasible",
                )
            )
    ranked.sort(key=lambda s: (s.deficit, s.typ.center_deg, s.typ.n_high))
    labels = tuple(s.label() for s in ranked)

    if gsign is None:
        extra = ""
        if ranked:
            extra = (
                f"; ranked residuals {len(ranked)} "
                "(cannot HIT until Σμ is forced)"
            )
        return DischargeResult(
            hit=False,
            reason=assert_sufficient_only(
                "inconclusive: global charge sign is not forced by μ on "
                f"{{D-1, D}}-vertices{extra} (proves nothing)"
            ),
            survivors=labels,
            ranked=tuple(ranked),
            checked=len(types),
            global_sign=None,
            intended_sign=isign,
        )

    if ranked:
        shown = "; ".join(labels[:8])
        extra = f" (+{len(ranked) - 8} more)" if len(ranked) > 8 else ""
        return DischargeResult(
            hit=False,
            reason=assert_sufficient_only(
                "inconclusive: argument does not close; surviving neighborhood "
                f"types: {shown}{extra} (proves nothing)"
            ),
            survivors=labels,
            ranked=tuple(ranked),
            checked=len(types),
            global_sign=gsign,
            intended_sign=isign,
        )
    return DischargeResult(
        hit=True,
        reason=assert_sufficient_only(
            f"𝒞 is UNAVOIDABLE in D-critical K_D-free graphs (D={arg.D}); "
            f"global Σμ has forced sign {gsign}, every non-excluded type meets "
            f"the opposite bound. {CLOSURE_TAG}"
        ),
        checked=len(types),
        global_sign=gsign,
        intended_sign=isign,
    )


def unavoidable_statement(arg: DischargingArgument, result: DischargeResult) -> str:
    cores = ",".join(arg.forbidden) if arg.forbidden else "(empty)"
    return assert_sufficient_only(
        f"UNAVOIDABLE (BK D={arg.D} discharging): cores={cores} "
        f"in every {arg.D}-critical K_{arg.D}-free graph. {result.reason}"
    )
