"""BK campaign staircase — next step from the ledger, not from prose.

The forever loop used to inject a generic “Continue.” That lets a model
rediscover C₄ every circuit. This module turns the append-only ledger +
working notebook into a countable stair: locked lemmas, distinct forbidden
cores, and the first incomplete increment.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

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
    "(new graph6 + degree spec, a kernel lemma, literature, or discharging).\n"
)
# Consecutive staircase injections with an unchanged progress fingerprint
# (after the catalogue/bridge stairs) before REFORMULATE fires.
STAGNATION_THRESHOLD = 2
# Legal discharging syntax if the model *chooses* that tool — not an assignment.
DISCHARGE_V1_HINT = (
    "If using discharging (optional): v1 D=9, μ keys 8 and 9; Σμ is forced if "
    "they share a strict sign, or μ(9)>0 and μ(8)≥0, or μ(9)<0 and μ(8)≤0. "
    "rules: from_deg 8 or 9, to_pattern deg8/deg9/low/high, radius 1, amount>0. "
    "forbidden = ledger C: graph6. Radius-1 degree charge cannot move "
    "deg9(high=9,low=0) — do not rerun search on that residual."
)
# After seeds: the whole instrument is in play. Discharging v1 is one tool.
OPEN_INSTRUMENT = (
    "Stand on Rabern's shoulders and try something new this circuit. "
    "literature_search / lean_search his papers and the corpus (Cranston–Rabern, "
    "Kierstead–Rabern, the dissertation, claw-free / hitting-cliques lines); "
    "extend a pinned result — do not rediscover it. Invent a NEW "
    "reducible_configuration (new graph6 + degree spec; not a listed core; "
    "an edge/K2 is not 1-choosable — do not mint it). Aim cores at the surviving "
    "neighborhood if one is listed (a 9-regular closed nbhd wants order ~10 "
    "dominating, not another μ). fixer_breaker / alon_tarsi / choosability_refute "
    "on new candidates. lean_prove a lemma that is not already locked "
    "(not equivalent_K3_join_E6, not K3JoinE6_*, not a dummy ..._durable closure). "
    "Discharging is optional and v1 cannot close deg9(high=9,low=0) — do not "
    "rerun discharging_search on that residual. Settlement is still durable "
    "borodinKostochka. Do not graph6_decode listed cores, do not SAT H??F~~~, "
    "do not rebuild the join."
)
REFORMULATE_BANNER = (
    "REFORMULATE: the ledger has not moved. Switch resource — do not rerun "
    "discharging_search with a new μ. " + OPEN_INSTRUMENT + " "
    "Do not lean_prove equivalent_K3_join_E6 (Literature sorry; same hardness as BK). "
    "Do not rebuild H??F~~~.\n"
)


@dataclass
class CampaignBind:
    """Live session pointers so ``campaign_status`` sees the current ledger.

    ``last_discharge_survivors`` is a neighborhood MISS from
    ``discharging_unavoidable`` / ``discharging_search`` (not a Claim — a
    miss proves nothing).
    ``last_discharge_note`` is the last engine reason even when survivors
    are empty (sign-unforced μ, coupling, illegal rules).
    ``last_search_banner`` is the latest ``DISCHARGING_SEARCH`` progress line.

    ``progress_fingerprint`` / ``stagnation_streak`` detect a frozen stair
    across staircase injections (not every continue).
    """

    ledger: Ledger | None = None
    notebook: LemmaNotebook | None = None
    last_discharge_survivors: tuple[str, ...] = ()
    last_discharge_note: str = ""
    last_search_banner: str = ""
    graph6_decode_counts: dict[str, int] = field(default_factory=dict)
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
    """Literature closure theorem, not session aliases (..._durable / ..._proved)."""
    key = _norm(name)
    if "reducibleandunavoidableimpnocounterexample" not in key:
        return False
    return not (key.endswith("durable") or key.endswith("proved"))


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


def _clip_note(note: str, n: int = 160) -> str:
    compact = " ".join(note.split())
    return compact if len(compact) <= n else compact[: n - 3] + "..."


def next_step(
    claims: Iterable[Claim],
    lemmas: Iterable[LockedLemma],
    *,
    survivors: tuple[str, ...] = (),
    discharge_note: str = "",
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
                f"{shown}{extra}. A miss proves nothing. Do not rerun "
                f"discharging_search on the same residual. {OPEN_INSTRUMENT}"
            )
        if discharge_note:
            clip = _clip_note(discharge_note)
            if "ledger coupling" in discharge_note:
                return (
                    f"last discharging used cores not on 𝒞: {clip}. "
                    f"{OPEN_INSTRUMENT}"
                )
            if "non-conserving" in discharge_note or "μ must specify" in discharge_note:
                return (
                    f"last discharging was illegal: {clip}. "
                    f"{DISCHARGE_V1_HINT} {OPEN_INSTRUMENT}"
                )
            return (
                f"last discharging did not close: {clip}. {OPEN_INSTRUMENT}"
            )
        return OPEN_INSTRUMENT
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
    discharge_note: str = "",
    search_banner: str = "",
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
    nxt = next_step(
        claim_list, lemma_list, survivors=survivors, discharge_note=discharge_note
    )
    if closed is not None:
        dis_line = f"  discharging: closed D=9 over {','.join(closed)}\n"
    elif survivors:
        shown_s = "; ".join(survivors[:4])
        more = f" (+{len(survivors) - 4} more)" if len(survivors) > 4 else ""
        dis_line = f"  discharging: not closed; last miss: {shown_s}{more}\n"
    elif discharge_note:
        dis_line = (
            "  discharging: not closed; last: "
            f"{_clip_note(discharge_note)}\n"
        )
    else:
        dis_line = "  discharging: not closed (no attempt)\n"
    if search_banner and closed is None:
        dis_line += f"  search: {search_banner}\n"
    return (
        f"{STAIRCASE_MARK}\n"
        f"  locked lemmas: {len(lemma_list)} ({len(durable)} durable)"
        f" — {shown}{extra}\n"
        f"  C: {len(cores)} cores — {core_part}\n"
        f"{bridge_line}"
        f"{seed_line}"
        f"{dis_line}"
        f"  NEXT: {nxt}\n"
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
        discharging = _residual_fingerprint(survivors)
    else:
        discharging = "open"
    return (durable, cores, discharging)


def _residual_fingerprint(survivors: tuple[str, ...]) -> str:
    """Collapse μ-oscillation on the same leftover type into one freeze key."""
    labels = tuple(
        s.split(" final=")[0].split(" deficit=")[0] for s in survivors if s
    )
    if any("deg9(high=9,low=0)" in lab for lab in labels):
        return "stuck:deg9-regular"
    return "miss:" + ";".join(labels) if labels else "open"


def stagnation_eligible(nxt: str) -> bool:
    """Catalogue and bridge stairs already prescribe the increment.

    REFORMULATE would tell the model to invent cores or skip the bridge.
    """
    return (
        "re-derive Rabern seed" not in nxt
        and "BK.reducible_of_fChoosable" not in nxt
    )


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
    discharge_note: str = "",
) -> str:
    """Tick freeze on a staircase injection. Return REFORMULATE or empty."""
    claim_list = list(claims)
    lemma_list = list(lemmas)
    nxt = next_step(
        claim_list, lemma_list, survivors=survivors, discharge_note=discharge_note
    )
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
        claims,
        lemmas,
        survivors=bind.last_discharge_survivors,
        discharge_note=bind.last_discharge_note,
        search_banner=getattr(bind, "last_search_banner", "") or "",
    )
    extra = stagnation_text(bind)
    return f"{snap}\n{extra}" if extra else snap
