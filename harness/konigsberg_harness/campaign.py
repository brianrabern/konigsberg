"""BK campaign staircase — next step from the ledger, not from prose.

The forever loop used to inject a generic “Continue.” That lets a model
rediscover C₄ every circuit. This module turns the append-only ledger +
working notebook into a countable stair: locked lemmas, distinct forbidden
cores, and the first incomplete increment.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from .ledger import Claim, Ledger, TrustRoot
from .lemmas import LemmaNotebook, LockedLemma

try:
    from konigsberg_empirical.reduction.reducible import bridge_is_formalized
    from konigsberg_empirical.reduction.seeds import (
        next_unminted_seed,
        seeds_rederived_count,
    )
except ImportError:  # pragma: no cover - empirical always installed with harness
    next_unminted_seed = None  # type: ignore[assignment]
    seeds_rederived_count = None  # type: ignore[assignment]

    def bridge_is_formalized() -> bool:  # type: ignore[misc]
        return False

STAIRCASE_MARK = "STAIRCASE (ledger, not prose):"
CORE_RE = re.compile(r"core=([^,\s]+)")
UNAVOIDABLE_CORES_RE = re.compile(r"cores=([^\s]+)")
CLOSURE_MARK = "conditional on discharging closure lemma"
REDISCOVERY_BANNER = (
    "REDISCOVERY: this core is already on the ledger. Do not retest it. "
    "Call campaign_status, then take the NEXT stair "
    "(new graph6 + degree spec, discharging_unavoidable, or a kernel lemma).\n"
)
# Consecutive staircase injections with an unchanged progress fingerprint
# (after the catalogue/bridge stairs) before REFORMULATE fires.
STAGNATION_THRESHOLD = 2
REFORMULATE_BANNER = (
    "REFORMULATE: the ledger has not moved on this stair. Rabern's meta-move "
    "is to trade the standing target for an a-priori-weaker equivalent — that "
    "is where choosability bites. literature_search "
    "CranstonRabern_BKEquivalentConjectures; pin equivalent_K3_join_E6 "
    "(χ=Δ=9 ⇒ contains K₃∗Ē₆ as a subgraph) and "
    "fChoosable_join_not_induced_in_critical (an f-choosable join A∗B with "
    "f(v)=d(v)−1 cannot be induced in a D-critical graph with Δ=D). One "
    "increment on the reformulated target (join core, or kernel work on the "
    "equivalence). Do not retest listed cores and do not drop the stair. "
    "Settlement is still durable borodinKostochka.\n"
)


@dataclass
class CampaignBind:
    """Live session pointers so ``campaign_status`` sees the current ledger.

    ``last_discharge_survivors`` is the best MISS from ``discharging_unavoidable``
    (not a Claim — a miss proves nothing). The snapshot shows it so the next
    increment can forbid that neighborhood.

    ``progress_fingerprint`` / ``stagnation_streak`` detect a frozen stair
    across staircase injections (not every continue).
    """

    ledger: Ledger | None = None
    notebook: LemmaNotebook | None = None
    last_discharge_survivors: tuple[str, ...] = ()
    progress_fingerprint: tuple | None = None
    stagnation_streak: int = 0


def extract_core(statement: str) -> str | None:
    if "FORBIDDEN CONFIGURATION" not in statement:
        return None
    m = CORE_RE.search(statement)
    return m.group(1) if m else None


def forbidden_cores(claims: Iterable[Claim]) -> tuple[str, ...]:
    seen: list[str] = []
    for claim in claims:
        core = extract_core(claim.statement)
        if core is not None and core not in seen:
            seen.append(core)
    return tuple(seen)


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def is_bridge_name(name: str) -> bool:
    return "reducibleoffchoosable" in _norm(name)


def is_closure_name(name: str) -> bool:
    key = _norm(name)
    return "reducibleandunavoidable" in key


def is_at_nine_name(name: str) -> bool:
    return "borodinkostochkaatnine" in _norm(name)


def _has_durable_named(
    claims: Iterable[Claim],
    lemmas: Iterable[LockedLemma],
    pred,
) -> bool:
    for lemma in lemmas:
        if lemma.durable and pred(lemma.lean_name):
            return True
    for claim in claims:
        if (
            claim.provenance.trust_root is TrustRoot.LEAN_KERNEL
            and claim.provenance.durable
            and pred(claim.statement)
        ):
            return True
    return False


def has_durable_bridge(
    claims: Iterable[Claim], lemmas: Iterable[LockedLemma]
) -> bool:
    if bridge_is_formalized():
        return True
    return _has_durable_named(claims, lemmas, is_bridge_name)


def has_durable_closure(
    claims: Iterable[Claim], lemmas: Iterable[LockedLemma]
) -> bool:
    return _has_durable_named(claims, lemmas, is_closure_name)


def has_durable_at_nine(
    claims: Iterable[Claim], lemmas: Iterable[LockedLemma]
) -> bool:
    return _has_durable_named(claims, lemmas, is_at_nine_name)


def extract_unavoidable_cores(statement: str) -> tuple[str, ...] | None:
    """Cores from a tagged UNAVOIDABLE Claim, or None if the Claim is not one.

    Fail-closed: missing closure tag ⇒ not a discharging HIT.
    """
    if "UNAVOIDABLE" not in statement or "D=9" not in statement:
        return None
    if CLOSURE_MARK not in statement:
        return None
    m = UNAVOIDABLE_CORES_RE.search(statement)
    if m is None:
        return None
    raw = m.group(1)
    if raw == "(empty)":
        return ()
    return tuple(c for c in raw.split(",") if c)


def discharging_closed(claims: Iterable[Claim]) -> tuple[str, ...] | None:
    """UNAVOIDABLE 𝒞 only if every named core is already minted reducible.

    Ledger coupling: an UNAVOIDABLE certificate over cores not on the
    forbidden-configuration ledger does not close the discharging half.
    """
    reducible = set(forbidden_cores(claims))
    for claim in claims:
        cores = extract_unavoidable_cores(claim.statement)
        if cores is None or not cores:
            continue
        if set(cores) <= reducible:
            return cores
    return None


def has_unavoidable(claims: Iterable[Claim]) -> bool:
    return discharging_closed(claims) is not None


def next_step(
    claims: Iterable[Claim],
    lemmas: Iterable[LockedLemma],
    *,
    survivors: tuple[str, ...] = (),
) -> str:
    claim_list = list(claims)
    lemma_list = list(lemmas)
    if not has_durable_bridge(claim_list, lemma_list):
        return (
            "durable lean_prove of BK.reducible_of_fChoosable "
            "(Literature.Coloring.BK_ReducibleOfFChoosable). "
            "The Literature entry is not yet formalized; forbidden configs "
            "stay conditional until this bridge is kernel-proved. "
            "Do not spend the circuit rediscovering C4/C6."
        )
    cores = forbidden_cores(claim_list)
    seed = next_unminted_seed(cores) if next_unminted_seed is not None else None
    if seed is not None:
        d_part = f", D={seed.D}" if seed.D is not None else ""
        return (
            f"re-derive Rabern seed {seed.name} via reducible_configuration "
            f"(core={seed.core}, degrees={list(seed.degrees)}{d_part}). "
            "Do not invent a new core until the catalogue is exhausted."
        )
    closed = discharging_closed(claim_list)
    if closed is None:
        if survivors:
            shown = "; ".join(survivors[:4])
            extra = f" (+{len(survivors) - 4} more)" if len(survivors) > 4 else ""
            return (
                "last discharging attempt did not close; surviving neighborhood: "
                f"{shown}{extra}. Forbid that neighborhood via "
                "reducible_configuration (targeted core) or repair μ/rules, "
                "then re-run discharging_unavoidable against ledger 𝒞 (D=9). "
                "A miss proves nothing."
            )
        return (
            "propose μ+rules and run discharging_unavoidable against "
            "ledger 𝒞 (D=9). The tool verifies; it does not invent. "
            "UNAVOIDABLE is sufficient-only; a MISS returns a surviving "
            "neighborhood and proves nothing. On a MISS, forbid that "
            "neighborhood or repair the rules."
        )
    if not has_durable_closure(claim_list, lemma_list):
        return (
            "durable lean_prove of "
            "BK.reducible_and_unavoidable_imp_no_counterexample "
            "(Literature.Coloring.BK_DischargingClosure). D=9 Claims stay "
            "conditional until this closure is kernel-proved. Requires the "
            f"reducible 𝒞 and UNAVOIDABLE certificate over {','.join(closed)}."
        )
    if not has_durable_at_nine(claim_list, lemma_list):
        return (
            "assemble: reducible 𝒞 + UNAVOIDABLE certificate ⇒ durable "
            "lean_prove of borodinKostochka_at_nine (BK at Δ=9). "
            "That milestone does not settle the general conjecture."
        )
    return (
        "durable lean_prove of borodinKostochka "
        "(χ ≤ max{Δ−1, ω} for Δ ≥ 9). A Δ=9 result is not this step."
    )


def format_campaign_snapshot(
    claims: Iterable[Claim],
    lemmas: Iterable[LockedLemma],
    *,
    survivors: tuple[str, ...] = (),
) -> str:
    claim_list = list(claims)
    lemma_list = list(lemmas)
    cores = forbidden_cores(claim_list)
    durable = [lemma for lemma in lemma_list if lemma.durable]
    names = [lemma.lean_name for lemma in lemma_list]
    shown = ", ".join(names[:12]) if names else "(none)"
    extra = "" if len(names) <= 12 else f" (+{len(names) - 12} more)"
    core_part = ", ".join(cores) if cores else "(none)"
    if bridge_is_formalized():
        bridge_line = "  bridge: BK.reducible_of_fChoosable formalized (Literature)\n"
    elif has_durable_bridge(claim_list, lemma_list):
        bridge_line = "  bridge: durable session proof (Literature still unformalized)\n"
    else:
        bridge_line = "  bridge: not formalized\n"
    if seeds_rederived_count is not None:
        done, total = seeds_rederived_count(cores)
        seed_line = f"  seeds: {done}/{total} re-derived\n"
    else:
        seed_line = ""
    closed = discharging_closed(claim_list)
    if closed is not None:
        dis_line = f"  discharging: closed D=9 over {','.join(closed)}\n"
    elif survivors:
        shown_s = "; ".join(survivors[:4])
        more = f" (+{len(survivors) - 4} more)" if len(survivors) > 4 else ""
        dis_line = f"  discharging: not closed; last miss: {shown_s}{more}\n"
    else:
        dis_line = "  discharging: not closed (no attempt)\n"
    return (
        f"{STAIRCASE_MARK}\n"
        f"  locked lemmas: {len(lemma_list)} ({len(durable)} durable)"
        f" — {shown}{extra}\n"
        f"  C: {len(cores)} cores — {core_part}\n"
        f"{bridge_line}"
        f"{seed_line}"
        f"{dis_line}"
        f"  NEXT: {next_step(claim_list, lemma_list, survivors=survivors)}\n"
        "Do not retest listed cores. One new increment this circuit. "
        "Read lemma_list / lemma_read before reproving."
    )


def progress_fingerprint(
    claims: Iterable[Claim],
    lemmas: Iterable[LockedLemma],
    *,
    survivors: tuple[str, ...] = (),
) -> tuple[tuple[str, ...], tuple[str, ...], str]:
    """Countable progress: durable lemma names, forbidden cores, discharging."""
    claim_list = list(claims)
    lemma_list = list(lemmas)
    durable = tuple(
        sorted(lemma.lean_name for lemma in lemma_list if lemma.durable)
    )
    cores = forbidden_cores(claim_list)
    closed = discharging_closed(claim_list)
    if closed is not None:
        discharging = "closed:" + ",".join(closed)
    elif survivors:
        discharging = "miss:" + ";".join(survivors)
    else:
        discharging = "open"
    return (durable, cores, discharging)


def stagnation_eligible(nxt: str) -> bool:
    """Catalogue and bridge stairs already prescribe the increment.

    REFORMULATE would tell the model to invent cores or skip the bridge.
    """
    if "re-derive Rabern seed" in nxt:
        return False
    if "BK.reducible_of_fChoosable" in nxt:
        return False
    return True


def stagnation_text(bind: CampaignBind) -> str:
    if bind.stagnation_streak >= STAGNATION_THRESHOLD:
        return REFORMULATE_BANNER
    return ""


def note_stagnation(
    bind: CampaignBind,
    claims: Iterable[Claim],
    lemmas: Iterable[LockedLemma],
    *,
    survivors: tuple[str, ...] = (),
) -> str:
    """Tick freeze on a staircase injection. Return REFORMULATE or empty."""
    claim_list = list(claims)
    lemma_list = list(lemmas)
    nxt = next_step(claim_list, lemma_list, survivors=survivors)
    fp = progress_fingerprint(claim_list, lemma_list, survivors=survivors)
    if not stagnation_eligible(nxt):
        bind.progress_fingerprint = fp
        bind.stagnation_streak = 0
        return ""
    if bind.progress_fingerprint == fp:
        bind.stagnation_streak += 1
    else:
        bind.progress_fingerprint = fp
        bind.stagnation_streak = 0
    return stagnation_text(bind)


def campaign_status(bind: CampaignBind) -> str:
    """Model-callable snapshot. Does not mint a Claim."""
    claims = bind.ledger.claims() if bind.ledger is not None else ()
    lemmas = bind.notebook.lemmas if bind.notebook is not None else ()
    snap = format_campaign_snapshot(
        claims, lemmas, survivors=bind.last_discharge_survivors
    )
    extra = stagnation_text(bind)
    return f"{snap}\n{extra}" if extra else snap
