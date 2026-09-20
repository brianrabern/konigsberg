"""Guided discharging search: cover survivors from the catalog, then mutate.

v1 survivors are ``LocalType`` degree signatures. Mechanical cover uses
``core_forced_in_type``, not induced subgraph of a graph6 neighborhood.
Only ledger-minted cores enter 𝒞. Unminted catalog hits are recorded, not
used for UNAVOIDABLE. STUCK is a residual, not a forbidden configuration.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..sufficient_only import assert_sufficient_only
from .catalog import (
    CatalogCover,
    CatalogEntry,
    cover_type,
    entries_from_cores,
    load_rabern_catalog,
)
from .engine import (
    MAX_FORBIDDEN,
    V1_D,
    DischargeRejected,
    DischargeResult,
    LocalType,
    Rule,
    Survivor,
    ToolBudgetExceeded,
    build_argument,
    verify_unavoidable,
)

DEFAULT_MAX_ITERS = 12
MAX_ITERS_CAP = 32
_TO_PATTERNS = ("low", "high")


@dataclass(frozen=True)
class SearchOutcome:
    status: str  # CLOSED | STUCK
    result: DischargeResult
    mu: dict[int, int]
    rules: tuple[Rule, ...]
    forbidden: tuple[str, ...]
    iterations: int
    covers_added: tuple[str, ...]
    unminted_covers: tuple[str, ...]
    history: tuple[tuple[int, int], ...]  # (survivors, deficit) per verify

    @property
    def residual(self) -> tuple[Survivor, ...]:
        return self.result.ranked


def format_search_banner(outcome: SearchOutcome) -> str:
    residual = (
        outcome.result.ranked[0].typ.label() if outcome.result.ranked else "-"
    )
    return assert_sufficient_only(
        f"DISCHARGING_SEARCH {outcome.status} "
        f"survivors={len(outcome.result.ranked)} "
        f"deficit={outcome.result.total_deficit} "
        f"C={len(outcome.forbidden)} iters={outcome.iterations} "
        f"residual={residual}"
    )


def frontier_statement(outcome: SearchOutcome) -> str:
    labels = [s.typ.label() for s in outcome.result.ranked[:8]]
    shown = ",".join(labels) if labels else "(none)"
    extra = (
        f" (+{len(outcome.result.ranked) - 8} more)"
        if len(outcome.result.ranked) > 8
        else ""
    )
    unminted = ""
    if outcome.unminted_covers:
        u = ",".join(outcome.unminted_covers[:6])
        more = (
            f" (+{len(outcome.unminted_covers) - 6})"
            if len(outcome.unminted_covers) > 6
            else ""
        )
        unminted = f"; unminted catalog covers={u}{more}"
    return assert_sufficient_only(
        f"{format_search_banner(outcome)}. IRREDUCIBLE-FRONTIER "
        f"(BK D={V1_D} discharging): residual types="
        f"{shown}{extra}{unminted} (proves nothing; not a forbidden "
        "configuration). Catalog cover + rule mutations did not close."
    )


def _coerce_mu(mu: dict) -> dict[int, int]:
    return {int(k): int(v) for k, v in mu.items()}


def _score(result: DischargeResult) -> tuple[int, int, int]:
    """Lexicographic: HIT first, then fewer survivors, then less deficit."""
    if result.hit:
        return (0, 0, 0)
    unforced = 1 if result.global_sign is None else 0
    return (1 + unforced, len(result.ranked), result.total_deficit)


def mutate_arguments(
    mu: dict[int, int], rules: tuple[Rule, ...]
) -> list[tuple[dict[int, int], tuple[Rule, ...]]]:
    """Small rule/μ library. No model. First improving mutation wins."""
    out: list[tuple[dict[int, int], tuple[Rule, ...]]] = []
    for d in (V1_D - 1, V1_D):
        bumped = dict(mu)
        bumped[d] = mu[d] + 1
        out.append((bumped, rules))
        dropped = dict(mu)
        dropped[d] = mu[d] - 1
        out.append((dropped, rules))
    existing = {(r.from_deg, r.to_pattern.lower(), r.amount) for r in rules}
    for from_deg in (V1_D - 1, V1_D):
        for pat in _TO_PATTERNS:
            key = (from_deg, pat, 1)
            if key in existing:
                continue
            extra = Rule(from_deg=from_deg, to_pattern=pat, amount=1)
            out.append((dict(mu), (*rules, extra)))
    if rules:
        r0 = rules[0]
        bumped_r = Rule(
            from_deg=r0.from_deg,
            to_pattern=r0.to_pattern,
            amount=r0.amount + 1,
            radius=r0.radius,
        )
        out.append((dict(mu), (bumped_r, *rules[1:])))
    return out


def _verify(
    D: int,
    mu: dict[int, int],
    rules: tuple[Rule, ...],
    forbidden: list[str],
    reducible: set[str] | frozenset[str],
) -> DischargeResult | None:
    arg = build_argument(D, mu, list(rules), forbidden)
    try:
        return verify_unavoidable(arg, reducible_cores=reducible)
    except (DischargeRejected, ToolBudgetExceeded):
        return None


def _add_covers(
    ranked: tuple[Survivor, ...],
    catalog: tuple[CatalogEntry, ...],
    forbidden: list[str],
    reducible: set[str] | frozenset[str],
    unminted: list[str],
) -> tuple[list[str], bool]:
    """Add minted catalog covers of residual types. Return (added, progressed)."""
    added: list[str] = []
    have = set(forbidden)
    for survivor in ranked:
        if len(have) >= MAX_FORBIDDEN:
            break
        typ: LocalType = survivor.typ
        minted_hit = cover_type(
            typ, catalog, minted=set(reducible), minted_only=True
        )
        if minted_hit is not None and minted_hit.entry.core not in have:
            have.add(minted_hit.entry.core)
            added.append(minted_hit.entry.core)
            continue
        hint = cover_type(typ, catalog, minted=set(reducible), minted_only=False)
        if (
            hint is not None
            and not hint.minted
            and hint.entry.core not in unminted
        ):
            unminted.append(hint.entry.core)
    if added:
        forbidden.extend(added)
        return added, True
    return [], False


def run_search(
    *,
    D: int = V1_D,
    mu: dict,
    rules: list | tuple,
    forbidden: list[str] | tuple[str, ...],
    reducible_cores: set[str] | frozenset[str],
    catalog: tuple[CatalogEntry, ...] | None = None,
    max_iters: int = DEFAULT_MAX_ITERS,
) -> SearchOutcome:
    """Drive survivor count down: minted covers first, then rule mutations."""
    if D != V1_D:
        raise DischargeRejected(f"v1 is D={V1_D} only (got D={D})")
    iters = max(1, min(int(max_iters), MAX_ITERS_CAP))
    live_mu = _coerce_mu(mu)
    arg0 = build_argument(D, live_mu, rules, forbidden)
    live_rules = arg0.rules
    live_c = list(arg0.forbidden)
    reducible = set(reducible_cores)
    cat = catalog if catalog is not None else load_rabern_catalog()
    cat = entries_from_cores(reducible) + tuple(cat)
    unminted: list[str] = []
    covers_added: list[str] = []
    history: list[tuple[int, int]] = []
    best: tuple[tuple[int, int, int], DischargeResult, dict, tuple[Rule, ...], tuple[str, ...]] | None = None

    last_result: DischargeResult | None = None
    used = 0
    for i in range(iters):
        used = i + 1
        result = _verify(D, live_mu, live_rules, live_c, reducible)
        if result is None:
            break
        last_result = result
        history.append((len(result.ranked), result.total_deficit))
        score = _score(result)
        snap = (score, result, dict(live_mu), live_rules, tuple(live_c))
        if best is None or score < best[0]:
            best = snap
        if result.hit:
            return SearchOutcome(
                status="CLOSED",
                result=result,
                mu=dict(live_mu),
                rules=live_rules,
                forbidden=tuple(live_c),
                iterations=used,
                covers_added=tuple(covers_added),
                unminted_covers=tuple(unminted),
                history=tuple(history),
            )
        added, progressed = _add_covers(
            result.ranked, cat, live_c, reducible, unminted
        )
        if progressed:
            covers_added.extend(added)
            continue
        improved = False
        for mu2, rules2 in mutate_arguments(live_mu, live_rules):
            cand = _verify(D, mu2, rules2, live_c, reducible)
            if cand is None:
                continue
            if _score(cand) < score:
                live_mu, live_rules = mu2, rules2
                improved = True
                break
        if not improved:
            break

    if last_result is None:
        raise DischargeRejected("discharging_search: argument did not verify")
    _, res, mu_b, rules_b, c_b = best if best is not None else (
        _score(last_result),
        last_result,
        live_mu,
        live_rules,
        tuple(live_c),
    )
    return SearchOutcome(
        status="STUCK",
        result=res,
        mu=mu_b,
        rules=rules_b,
        forbidden=c_b,
        iterations=used,
        covers_added=tuple(covers_added),
        unminted_covers=tuple(unminted),
        history=tuple(history),
    )


def describe_cover(cover: CatalogCover | None, typ: LocalType) -> str:
    if cover is None:
        return assert_sufficient_only(
            f"no catalog cover for {typ.label()} via core_forced_in_type"
        )
    grade = "offline/AT" if cover.entry.proof_grade else "online/k-fold"
    mint = "minted" if cover.minted else "unminted"
    return assert_sufficient_only(
        f"cover {typ.label()} → {cover.entry.core} ({cover.entry.name}, "
        f"n={cover.entry.n}, {grade}, {mint})"
    )
