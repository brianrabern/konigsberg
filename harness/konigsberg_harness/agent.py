"""The agent loop.

Deliberately a simple while-loop over a rich tool registry. No orchestration
graphs, no multi-agent architecture in v1 (add only when measurably justified).

The loop closes on *context assembly*: each ``step`` rebuilds the model context
from ``session.history`` + tool schemas, calls ``model.respond``, and yields
events as they happen so a REPL can render/steer live.

Trust invariant: only a tool-minted ``Claim`` enters the ledger; an
``AssistantFinal`` mints nothing. Final answers are rendered in Established
(ledger) vs Commentary (model prose) zones — see ``grounding``.
"""
from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

from pydantic import ValidationError

from .campaign import (
    REDISCOVERY_BANNER,
    STAIRCASE_MARK,
    extract_core,
    forbidden_cores,
    format_campaign_snapshot,
    note_stagnation,
    stagnation_text,
)
from .compaction import CompactionConfig, compact, should_compact
from .grounding import format_grounded_answer
from .ledger import Claim, EvidenceKind, Ledger, TrustRoot
from .lemmas import LockedLemma, lemma_has_hole
from .models import (
    AssistantText,
    Model,
    Tier,
    ToolCall,
    ToolResultMsg,
    UserMsg,
)
from .session import Session, SessionStore
from .tools.errors import ToolBudgetExceeded, ToolUnavailable
from .tools.registry import ToolRegistry


@dataclass
class AgentConfig:
    max_steps: int = 40
    hunt: bool = False  # do not stop on prose; continue until lean_prove
    hunt_max_rounds: int = 200  # ≤0 means unlimited (forever campaign)
    hunt_require_durable: bool = False
    hunt_forever: bool = False  # campaign: stop only if BK is proved or disproved
    compaction: CompactionConfig | None = None


@dataclass
class Observation:
    """One tool observation (headless transcript compatibility)."""

    action: object
    result: str
    is_error: bool = False
    unavailable: bool = False


@dataclass
class AgentResult:
    final: str | None
    ledger: Ledger
    steps: int
    transcript: list[Observation] = field(default_factory=list)
    session: Session | None = None
    commentary: str | None = None


# --- Live events (REPL renders these) -------------------------------------


@dataclass(frozen=True)
class ModelThinking:
    """Emitted immediately before a model.respond call so the REPL can spin."""

    message: str = "Thinking…"


@dataclass(frozen=True)
class ToolCallProposed:
    call: ToolCall


@dataclass(frozen=True)
class ToolResult:
    call: ToolCall
    content: str
    is_error: bool = False
    unavailable: bool = False


@dataclass(frozen=True)
class ClaimMinted:
    claim: Claim


@dataclass(frozen=True)
class AssistantFinal:
    """Final answer: ``text`` is the zone render; ``commentary`` is raw prose."""

    text: str
    commentary: str
    claims: tuple[Claim, ...] = ()
    failures: tuple[str, ...] = ()
    references: tuple[dict, ...] = ()
    definitions: tuple[str, ...] = ()


@dataclass(frozen=True)
class Interrupted:
    """Emitted when ``request_interrupt`` was set; session left consistent."""


@dataclass(frozen=True)
class HuntContinued:
    """Hunt mode: model tried to stop in prose without a lean_prove hit."""

    preview: str = ""


AgentEvent = (
    ModelThinking
    | ToolCallProposed
    | ToolResult
    | ClaimMinted
    | AssistantFinal
    | Interrupted
    | HuntContinued
)

HUNT_CONTINUE = (
    "HUNT MODE: that was commentary, not a kernel proof. Continue. "
    "Call lean_prove on a lemma or theorem. Read prior locks with lemma_list / "
    "lemma_read and reuse them. Do not finish in prose until lean_prove succeeds."
)

HUNT_KICKOFF = (
    "HUNT MODE: keep going until a lemma or theorem is kernel-checked via "
    "lean_prove. Lock proofs with lean_prove; reread them with lemma_list / "
    "lemma_read. Do not stop in prose until that proof exists."
)

BK_CAMPAIGN_TASK = (
    "Campaign: prove or disprove the Borodin–Kostochka conjecture "
    "(every graph with Δ ≥ 9 has χ ≤ max{Δ−1, ω}). "
    "Build on Rabern's results already in this corpus — RabernBook list "
    "bounds, BasicIrreducible, kernel-perfect list coloring, "
    "4-list-critical / Cranston–Rabern edge bounds, Kierstead–Rabern "
    "Ore-Vizing, hitting maximum cliques, and the reducible-configuration "
    "/ f-choosability line — rather than starting from scratch. "
    "literature_search Rabern first; pin statements; extend them. "
    "It is open — never claim it is settled in prose. You prove it with a "
    "durable lean_prove of borodinKostochka (kernel-checked χ ≤ max{Δ−1, ω} "
    "for Δ ≥ 9). A certified bk_predicate VIOLATES disproves it. Otherwise "
    "keep making kernel-checked and certificate-checked increments."
)

FOREVER_KICKOFF = """\
FOREVER CAMPAIGN — Borodin–Kostochka. Do not stop in prose.
Halt only when the ledger settles the conjecture:
  proved    = durable lean_prove of borodinKostochka (kernel-checked
              χ ≤ max{Δ−1, ω} for Δ ≥ 9). That Claim IS a proof.
  disproved = bk_predicate VIOLATES (certified Δ≥9 counterexample).
A durable proof of borodinKostochka_at_nine is a Δ=9 milestone, not halt.
The corpus statement is
  Konigsberg.Literature.Coloring.BorodinKostochka.borodinKostochka
(stated, sorry). You cannot overwrite the imported decl; a settlement
proof is a complete theorem whose lean_name contains BorodinKostochka
and whose type is the Δ ≥ 9 statement (not the = 9 slice).
Ordinary lemmas lock and the campaign continues. Ctrl-C also stops.
Build on Rabern, do not restart from Brooks: literature_search Rabern /
CranstonRabern / KiersteadRabern / RabernBook before inventing lemmas.
Extend those results into the H_BK reducible-configuration program.
Use the full instrument on every circuit, not a subset. After Rabern seeds
are on 𝒞, NEXT is whichever unused resource can produce a new locked lemma,
a new forbidden core, or a real discharging close — not another μ on the
same residual. Discharging v1 (radius-1, degree charge) cannot move
deg9(high=9,low=0); switch to a new core, literature, Lean, or another
checker instead of rerunning discharging_search.
- Corpus: literature_search, lean_search. arxiv_search for leads only.
  Pin CranstonRabern_BKEquivalentConjectures (f-choosable joins / K₃∗Ē₆),
  CranstonRabern_ChiEqDeltaBigCliques, CranstonRabern_BrooksAndBeyond
  (χ, χ_ℓ ≤ max{3, ω, Δ}; independence lemma), Rabern_HittingMaxCliques, the
  dissertation citation, claw-free BK, doubly-critical-edge BK.
- Bridge: BK.reducible_of_fChoosable is formalized in Literature — do not re-prove it.
- Reducible configs: reducible_configuration under H_BK (sufficient-only).
- Discharging: discharging_search / discharging_unavoidable (v1 D=9) VERIFY;
  they do not invent. Optional after seeds, not the only stair.
- Empirical BK: bk_predicate, bk_search (refutation only), choosability_refute, alon_tarsi, fixer_breaker, list_critical, decide_colorable, chromatic_number.
- Graphs: make_graph, blow_up, mycielskian, clique_number, max_degree, independent_hitting_set.
- Lean: lean_typecheck_statement, lean_check, lean_prove, lemma_list, lemma_read.
- Staircase: campaign_status — locked lemmas, known cores, discharging closed/not, the NEXT increment.
Lock every successful lean_prove and reuse it. A finite sweep never proves BK.
Progress = locked lemmas + new forbidden cores + a closing discharging argument + repaired statements + kernel subproofs.
Staircase (first incomplete step; one increment per circuit; any listed tool is legal after seeds):
  1. Re-derive Rabern's seed configs (campaign_status lists seeds k/N), then a new core.
  2. Open discharging stair: new core, literature pin, kernel lemma, fixer_breaker/AT,
     or discharging only with a new idea — not another search on deg9(high=9,low=0).
  3. Durable lean_prove of BK.reducible_and_unavoidable_imp_no_counterexample, then borodinKostochka_at_nine (Δ=9 milestone, not halt).
  4. Durable lean_prove of borodinKostochka (Δ ≥ 9).
Call campaign_status after compaction. Do not retest listed cores. Exhaust the
Rabern catalogue before inventing configurations. Class-restricted BK is reference, not a target.
If the stair freezes (same |𝒞|, same durable lemmas, same residual),
REFORMULATE: switch resource. Do not prove equivalent_K3_join_E6
(Literature sorry) and do not SAT-search K₃∨Ē₆ / H??F~~~ (already on 𝒞).
"""

FOREVER_CONTINUE = (
    "CAMPAIGN: commentary is not a stopping point. Borodin–Kostochka is still open. "
    "Stop only on a durable kernel proof of borodinKostochka (Δ ≥ 9) or a "
    "bk_predicate VIOLATES. borodinKostochka_at_nine is a Δ=9 milestone, not halt. "
    "That kernel Claim of the general statement is a proof of the conjecture. "
    "Build on Rabern (literature_search) — extend those results, do not "
    "rediscover named theorems. Take the NEXT stair below — not a core already "
    "listed. Call campaign_status if the stair is missing. Be creative: a new "
    "core, a pinned literature lemma, fixer_breaker/AT, or a real lean_prove "
    "all count. A reducible_configuration MISS is sufficient-only — do not repeat the "
    "same core+degrees. Listed cores are done — do not reducible_configuration, "
    "choosability_refute, or re-join them (including H??F~~~ / K₃∨Ē₆). "
    "A sorry/admit lock is not progress. A lean_prove compile miss is not a "
    "kernel proof — do not resubmit the same snippet or `import` lines "
    "(scratch env already has Konigsberg). graph6_decode of a listed core or "
    "the same string is not an increment. K3JoinE6_adj is locked — do not prove "
    "degreeSpec / adj_iff of the join. REFORMULATE means switch resource "
    "(new core, literature, Lean, fixer_breaker) — not another discharging_search "
    "μ on deg9(high=9,low=0), and not SAT/Lean fishing on the join gadget. Continue."
)

CAMPAIGN_PROVED = (
    "Campaign stopped: Borodin–Kostochka PROVED "
    "(durable kernel proof of the conjecture)."
)
CAMPAIGN_DISPROVED = (
    "Campaign stopped: Borodin–Kostochka DISPROVED "
    "(certified counterexample, Δ ≥ 9)."
)


def _hunt_kickoff_text(config: AgentConfig) -> str:
    return FOREVER_KICKOFF if config.hunt_forever else HUNT_KICKOFF


def _hunt_continue_text(
    config: AgentConfig,
    session: Session | None = None,
    *,
    survivors: tuple[str, ...] = (),
    discharge_note: str = "",
    stagnation: str = "",
) -> str:
    if not config.hunt_forever:
        return HUNT_CONTINUE
    if session is None:
        return FOREVER_CONTINUE
    snap = format_campaign_snapshot(
        session.ledger.claims(),
        session.notebook.lemmas,
        survivors=survivors,
        discharge_note=discharge_note,
    )
    if stagnation:
        return f"{FOREVER_CONTINUE}\n\n{snap}\n{stagnation}"
    return f"{FOREVER_CONTINUE}\n\n{snap}"


def _render_result(result: object) -> str:
    if isinstance(result, list):
        return "results: " + ("; ".join(map(str, result)) if result else "(none)")
    return str(result)


def _claims_from_result(result: object) -> list[Claim] | None:
    """Extract minted Claims from a tool result (single or bundle)."""
    if isinstance(result, Claim):
        return [result]
    if (
        isinstance(result, (list, tuple))
        and result
        and all(isinstance(c, Claim) for c in result)
    ):
        return list(result)
    return None


def _literature_hits_from_result(result: object) -> list[dict] | None:
    """Detect literature_search hit dicts (status-bearing; not Claims)."""
    if not isinstance(result, list) or not result:
        return None
    if all(
        isinstance(d, dict) and "status" in d and "lean_name" in d and "name" in d
        for d in result
    ):
        return list(result)
    return None


def _arxiv_hits_from_result(result: object) -> list[dict] | None:
    """Detect arxiv_search hit dicts (bibliographic; not Claims)."""
    if not isinstance(result, list) or not result:
        return None
    if all(
        isinstance(d, dict)
        and d.get("source") == "arxiv"
        and "arxiv_id" in d
        and "title" in d
        for d in result
    ):
        return list(result)
    return None


def _is_hunt_proof(claim: Claim, *, require_durable: bool) -> bool:
    """True when this Claim is the hunt stop condition (lean_prove kernel proof)."""
    p = claim.provenance
    if p.tool != "lean_prove":
        return False
    if p.trust_root is not TrustRoot.LEAN_KERNEL:
        return False
    if p.evidence_kind is not EvidenceKind.PROOF:
        return False
    return p.durable if require_durable else True


def _normalized_ident(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def _is_bk_conjecture_name(name: str) -> bool:
    """True for names that denote the conjecture itself, not a BK-adjacent lemma.

    Slice results (``borodinKostochka_at_nine`` and similar) are deliberately
    excluded: a D=9 proof must never flip the general campaign settlement.
    """
    key = _normalized_ident(name)
    if "reducible" in key or "fchoosable" in key:
        return False
    if "atnine" in key or re.search(r"at\d+", key):
        return False
    if "dischargingclosure" in key:
        return False
    return "borodinkostochka" in key or key in {
        "bkconjecture",
        "borodinkostochkaconjecture",
    }


def _snippet_looks_like_bk(snippet: str) -> bool:
    """Cheap guard against `theorem BorodinKostochka : True := trivial`.

    A keyword heuristic only — NOT sufficient at the halting boundary. Used as a
    fallback for callers with no Lean REPL (unit tests); the live campaign gates
    settlement on a kernel type-equality check instead (see ``_bk_settlement_snippet``
    / ``Agent._verify_bk_settlement``).
    """
    src = snippet.lower()
    has_nine = bool(re.search(r"(≥|>=|ge\s)\s*9|\b9\s*(≤|<=|le\s)", src))
    has_delta = any(t in src for t in ("maxdegree", "max_degree", "delta", "Δ", "δ"))
    has_chi = any(t in src for t in ("chromatic", "colorable"))
    has_omega = any(t in src for t in ("clique", "omega", "ω"))
    return has_nine and has_delta and has_chi and has_omega


# Fully-qualified corpus statement whose proof settles the campaign.
BK_CORPUS_DECL = "Konigsberg.Literature.Coloring.BorodinKostochka.borodinKostochka"
BK_AT_NINE_DECL = (
    "Konigsberg.Literature.Coloring.BK_DischargingClosure.borodinKostochka_at_nine"
)


def _bk_settlement_snippet(proved_name: str) -> str:
    """Kernel proof-irrelevance check that ``proved_name`` proves EXACTLY the
    corpus Borodin–Kostochka statement.

    ``Eq`` forces both sides to share a type, so if ``proved_name``'s proposition
    differs from the corpus statement the ``example`` fails to elaborate; if it
    matches, Prop proof-irrelevance closes it by ``rfl``. This is what makes a
    ``PROVED`` halt trustworthy — a keyword match on the snippet is not. The
    check is intentionally exact (defeq): a genuine proof stated in a different
    but equivalent form is a *false negative* (campaign keeps hunting, the
    durable BK-named Claim sits on the ledger for a human), which is the safe
    direction. A false positive is the one outcome we must never produce.
    """
    return f"example : @{BK_CORPUS_DECL} = @{proved_name} := rfl"


def _bk_at_nine_settlement_snippet(proved_name: str) -> str:
    """Kernel proof-irrelevance check against the D=9 corpus statement.

    Distinct from ``_bk_settlement_snippet``: defeq to ``borodinKostochka_at_nine``
    is a Δ=9 milestone, never general-campaign settlement.
    """
    return f"example : @{BK_AT_NINE_DECL} = @{proved_name} := rfl"


def _is_bk_at_nine_name(name: str) -> bool:
    return "borodinkostochkaatnine" in _normalized_ident(name)


def _snippet_looks_like_bk_at_nine(snippet: str) -> bool:
    """Heuristic for callers with no REPL. Not the live-campaign gate."""
    src = snippet.lower()
    has_eq_nine = bool(re.search(r"maxdegree\s*=\s*9", src))
    has_ge_nine = bool(re.search(r"(≥|>=|ge\s)\s*9|\b9\s*(≤|<=|le\s)", src))
    if has_ge_nine or not has_eq_nine:
        return False
    has_chi = "colorable" in src
    has_omega = any(t in src for t in ("clique", "omega", "ω"))
    return has_chi and has_omega


def campaign_settlement(
    claim: Claim,
    call: ToolCall | None = None,
    *,
    verify_type: Callable[[str], bool] | None = None,
) -> str | None:
    """Return ``proved`` / ``disproved`` if this Claim settles Borodin–Kostochka.

    Disproof is a ``bk_predicate`` certificate that the graph VIOLATES under
    Δ ≥ 9. Proof is a *durable*, axiom-clean kernel ``lean_prove`` whose target
    is named for the conjecture AND whose type is verified equal to the corpus
    BK statement.

    ``verify_type(lean_name) -> bool`` is the kernel check (supplied by the live
    campaign via ``Agent._verify_bk_settlement``). When it is ``None`` — a caller
    with no Lean REPL, e.g. a unit test — we fall back to the cheap
    ``_snippet_looks_like_bk`` heuristic, which is NOT trustworthy on its own and
    must never gate a real campaign. A ``PROVED`` halt in production requires the
    kernel check to pass; anything less returns ``None`` (keep hunting).
    """
    p = claim.provenance
    if (
        p.tool.startswith("bk_predicate")
        and p.trust_root is TrustRoot.CERTIFICATE
        and "VIOLATES BK" in claim.statement
    ):
        return "disproved"
    if not (
        p.tool == "lean_prove"
        and p.trust_root is TrustRoot.LEAN_KERNEL
        and p.evidence_kind is EvidenceKind.PROOF
        and p.durable
    ):
        return None
    # A settlement proof must be axiom-clean: a "proof" routed through the corpus
    # `sorry` decl (or via native_decide) carries a nonstandard axiom and is not BK.
    if p.nonstandard_axioms:
        return None
    name = claim.statement
    snippet = ""
    if call is not None:
        name = str(call.args.get("lean_name") or claim.statement)
        snippet = str(call.args.get("snippet") or "")
    if not _is_bk_conjecture_name(name):
        return None
    # Halting boundary: prefer the kernel type-equality check over any heuristic.
    if verify_type is not None:
        return "proved" if verify_type(name) else None
    if not _snippet_looks_like_bk(snippet):
        return None
    return "proved"


def settles_bk_at(
    claim: Claim,
    call: ToolCall | None = None,
    *,
    D: int = 9,
    verify_type: Callable[[str], bool] | None = None,
) -> int | None:
    """Return ``D`` if this Claim is a kernel proof of BK at that Δ, else None.

    v1 recognizes only D=9, via kernel defeq to ``borodinKostochka_at_nine``.
    This is a milestone recognizer — it must never be wired as
    ``campaign_settlement`` ``proved``. A D=9 result does not halt ``--forever``.
    """
    if D != 9:
        return None
    p = claim.provenance
    if not (
        p.tool == "lean_prove"
        and p.trust_root is TrustRoot.LEAN_KERNEL
        and p.evidence_kind is EvidenceKind.PROOF
        and p.durable
    ):
        return None
    if p.nonstandard_axioms:
        return None
    name = claim.statement
    snippet = ""
    if call is not None:
        name = str(call.args.get("lean_name") or claim.statement)
        snippet = str(call.args.get("snippet") or "")
    if not _is_bk_at_nine_name(name):
        return None
    if verify_type is not None:
        return 9 if verify_type(name) else None
    if not _snippet_looks_like_bk_at_nine(snippet):
        return None
    return 9


def _hunt_stop_commentary(settlement: str | None) -> str:
    if settlement == "disproved":
        return CAMPAIGN_DISPROVED
    if settlement == "proved":
        return CAMPAIGN_PROVED
    return "Hunt stopped: kernel-checked proof locked."


def _lock_from_prove(
    session: Session, call: ToolCall, claim: Claim, store: SessionStore | None
) -> None:
    snippet = str(call.args.get("snippet") or "")
    name = str(call.args.get("lean_name") or claim.statement)
    if not snippet.strip() or not name:
        return
    lemma = LockedLemma(
        lean_name=name,
        snippet=snippet,
        durable=bool(claim.provenance.durable),
        axioms=tuple(claim.provenance.axioms),
    )
    if lemma_has_hole(lemma):
        return
    if store is not None:
        store.log_lemma(session, lemma)
    else:
        session.notebook.lock(lemma)


def _seed_user_message(task: str) -> UserMsg:
    return UserMsg(
        f"{task}\n\n"
        "Use the available tools to make progress. When finished, reply with a "
        "short plain-text summary (no tool call). Mathematical verdicts must be "
        "backed by ledger Claims from tools; if a tool fails, report not established."
    )


class Agent:
    def __init__(
        self, registry: ToolRegistry, model: Model, config: AgentConfig | None = None
    ) -> None:
        self.registry = registry
        self.model = model
        self.ledger = Ledger()  # last-run mirror for callers that still read it
        self.config = config or AgentConfig()
        self._interrupt = False
        self._rounds = 0

    def _verify_bk_settlement(self, proved_name: str) -> bool:
        """Kernel-check that ``proved_name`` proves the corpus BK statement.

        Fail-closed: a missing ``lean_check`` tool (no live REPL), any dispatch
        error, or a non-ok elaboration all mean 'not settled' — never a false
        PROVED. This is the trust boundary for the campaign's halt.
        """
        try:
            state = self.registry.dispatch(
                "lean_check", {"snippet": _bk_settlement_snippet(proved_name)}
            )
        except Exception:  # noqa: BLE001 — any failure ⇒ not settled (fail-closed)
            return False
        return bool(getattr(state, "ok", False))

    def _verify_bk_at_nine(self, proved_name: str) -> bool:
        """Kernel-check that ``proved_name`` proves BK at Δ=9, not the general conjecture."""
        try:
            state = self.registry.dispatch(
                "lean_check", {"snippet": _bk_at_nine_settlement_snippet(proved_name)}
            )
        except Exception:  # noqa: BLE001 — any failure ⇒ not a D=9 milestone
            return False
        return bool(getattr(state, "ok", False))

    def request_interrupt(self) -> None:
        """Ask ``step`` to halt at the next event boundary (Ctrl-C path)."""
        self._interrupt = True

    def clear_interrupt(self) -> None:
        self._interrupt = False

    def _persist_item(
        self, session: Session, item: object, store: SessionStore | None
    ) -> None:
        if store is not None:
            store.log_history_item(session, item)  # type: ignore[arg-type]
        else:
            session.history.append(item)  # type: ignore[arg-type]
            session.touch()

    def _persist_claim(
        self, session: Session, claim: Claim, store: SessionStore | None
    ) -> None:
        if store is not None:
            store.log_claim(session, claim)
        else:
            session.ledger.record(claim)
            session.touch()

    def _bind_campaign(self, session: Session) -> None:
        bind = getattr(self.registry, "campaign_bind", None)
        if bind is not None:
            if bind.ledger is not session.ledger:
                bind.progress_fingerprint = None
                bind.stagnation_streak = 0
            bind.ledger = session.ledger
            bind.notebook = session.notebook

    def _discharge_survivors(self) -> tuple[str, ...]:
        bind = getattr(self.registry, "campaign_bind", None)
        if bind is None:
            return ()
        return tuple(getattr(bind, "last_discharge_survivors", ()) or ())

    def _discharge_note(self) -> str:
        bind = getattr(self.registry, "campaign_bind", None)
        if bind is None:
            return ""
        return str(getattr(bind, "last_discharge_note", "") or "")

    def _stagnation_note(self) -> str:
        bind = getattr(self.registry, "campaign_bind", None)
        if bind is None:
            return ""
        return stagnation_text(bind)

    def _staircase_snapshot(self, session: Session, *, tick: bool = False) -> str:
        claims = session.ledger.claims()
        lemmas = session.notebook.lemmas
        survivors = self._discharge_survivors()
        note = self._discharge_note()
        snap = format_campaign_snapshot(
            claims, lemmas, survivors=survivors, discharge_note=note
        )
        bind = getattr(self.registry, "campaign_bind", None)
        extra = ""
        if bind is not None:
            extra = (
                note_stagnation(
                    bind, claims, lemmas, survivors=survivors, discharge_note=note
                )
                if tick
                else stagnation_text(bind)
            )
        return f"{snap}\n{extra}" if extra else snap

    def _maybe_inject_staircase(
        self,
        session: Session,
        store: SessionStore | None,
        *,
        force: bool = False,
    ) -> None:
        """Keep the next increment in chat after compaction / long tool chains."""
        if not self.config.hunt_forever:
            return
        if not force and (self._rounds == 1 or self._rounds % 5 != 1):
            return
        if session.history:
            last = session.history[-1]
            if isinstance(last, UserMsg) and STAIRCASE_MARK in last.text:
                return
        snap = self._staircase_snapshot(session, tick=True)
        self._persist_item(session, UserMsg(snap), store)

    def step(
        self,
        session: Session,
        *,
        store: SessionStore | None = None,
        tier: Tier = Tier.FRONTIER,
    ) -> Iterator[AgentEvent]:
        """Drive until AssistantFinal, interrupt, or the round cap.

        Chat mode (default): stop on the first prose turn, or ``max_steps``.
        Hunt mode: ignore prose finals until a ``lean_prove`` kernel proof, or
        ``hunt_max_rounds`` (≤0 = unlimited). Forever hunt ignores ordinary
        lemmas and stops only if the target conjecture is proved or disproved
        (or interrupt / cap).
        """
        self.clear_interrupt()
        self._rounds = 0
        tools = self.registry.tool_specs()
        turn_claims: list[Claim] = []
        turn_failures: list[str] = []
        turn_refs: list[dict] = []
        turn_definitions: list[str] = []
        hunt_hit = False
        hunt_settlement: str | None = None

        while True:
            if self._interrupt:
                yield Interrupted()
                return
            if self.config.hunt:
                cap = self.config.hunt_max_rounds
                if cap > 0 and self._rounds >= cap:
                    return
            elif self._rounds >= self.config.max_steps:
                return

            self._rounds += 1
            self._bind_campaign(session)
            compacted = False
            cfg = self.config.compaction
            if self.config.hunt and cfg is not None and should_compact(session, cfg):
                compact(session, self.model, config=cfg, store=store)
                compacted = True
            self._maybe_inject_staircase(session, store, force=compacted)
            yield ModelThinking("Thinking…")
            try:
                turn = self.model.respond(session.history, tools, tier=tier)
            except (TimeoutError, RuntimeError) as e:
                # --forever must not die on a silent LLM (Eva does not stream;
                # urllib timeout is idle-on-socket, not "generation finished").
                if not self.config.hunt_forever:
                    raise
                timed_out = isinstance(e, TimeoutError) or "timed out" in str(e).lower()
                if not timed_out:
                    raise
                turn = AssistantText(f"(LLM request timed out: {e})")

            if isinstance(turn, AssistantText):
                keep_hunting = self.config.hunt and (
                    self.config.hunt_forever or not hunt_hit
                )
                if keep_hunting:
                    self._persist_item(session, turn, store)
                    yield HuntContinued(preview=turn.text[:200])
                    self._persist_item(
                        session,
                        UserMsg(
                            _hunt_continue_text(
                                self.config,
                                session,
                                survivors=self._discharge_survivors(),
                                discharge_note=self._discharge_note(),
                                stagnation=self._stagnation_note(),
                            )
                        ),
                        store,
                    )
                    continue
                self._persist_item(session, turn, store)
                grounded = format_grounded_answer(
                    commentary=turn.text,
                    claims=turn_claims,
                    failures=turn_failures,
                    references=turn_refs,
                    definitions=turn_definitions,
                )
                yield AssistantFinal(
                    text=grounded,
                    commentary=turn.text,
                    claims=tuple(turn_claims),
                    failures=tuple(turn_failures),
                    references=tuple(turn_refs),
                    definitions=tuple(turn_definitions),
                )
                return

            # Record the whole assistant tool-use turn first (API requires matching
            # tool_results before the next respond).
            unanswered = list(turn)
            for call in turn:
                self._persist_item(session, call, store)
                yield ToolCallProposed(call)
                if self._interrupt:
                    for rest in unanswered:
                        tr = ToolResultMsg(
                            id=rest.id,
                            content="ERROR Interrupted",
                            is_error=True,
                        )
                        self._persist_item(session, tr, store)
                        yield ToolResult(call=rest, content=tr.content, is_error=True)
                    yield Interrupted()
                    return

            for call in turn:
                unanswered = [c for c in unanswered if c.id != call.id]
                try:
                    result = self.registry.dispatch(call.name, call.args)
                    if call.name == "list_critical":
                        from .tools.empirical_tools import list_critical_definition

                        m = call.args.get("m")
                        if isinstance(m, int):
                            turn_definitions.append(list_critical_definition(m))
                except (ToolUnavailable, ToolBudgetExceeded) as e:
                    banner = e.banner()
                    turn_failures.append(e.tool)
                    tr = ToolResultMsg(id=call.id, content=banner, is_error=True)
                    self._persist_item(session, tr, store)
                    yield ToolResult(
                        call=call, content=banner, is_error=True, unavailable=True
                    )
                    if self._interrupt:
                        for rest in unanswered:
                            tr = ToolResultMsg(
                                id=rest.id,
                                content="ERROR Interrupted",
                                is_error=True,
                            )
                            self._persist_item(session, tr, store)
                            yield ToolResult(call=rest, content=tr.content, is_error=True)
                        yield Interrupted()
                        return
                    continue
                except (ValidationError, Exception) as e:  # noqa: BLE001
                    err = f"ERROR {type(e).__name__}: {e}"
                    turn_failures.append(call.name)
                    tr = ToolResultMsg(id=call.id, content=err, is_error=True)
                    self._persist_item(session, tr, store)
                    yield ToolResult(call=call, content=err, is_error=True)
                    if self._interrupt:
                        for rest in unanswered:
                            tr = ToolResultMsg(
                                id=rest.id,
                                content="ERROR Interrupted",
                                is_error=True,
                            )
                            self._persist_item(session, tr, store)
                            yield ToolResult(call=rest, content=tr.content, is_error=True)
                        yield Interrupted()
                        return
                    continue

                claims = _claims_from_result(result)
                if claims is not None:
                    prior_cores = forbidden_cores(session.ledger.claims())
                    for claim in claims:
                        self._persist_claim(session, claim, store)
                        turn_claims.append(claim)
                    rendered = (
                        claims[0].render()
                        if len(claims) == 1
                        else "\n".join(c.render() for c in claims)
                    )
                    if call.name == "reducible_configuration":
                        core = extract_core(claims[0].statement)
                        if core is not None and core in prior_cores:
                            rendered = REDISCOVERY_BANNER + rendered
                    tr = ToolResultMsg(id=call.id, content=rendered)
                    self._persist_item(session, tr, store)
                    yield ToolResult(call=call, content=rendered, is_error=False)
                    for claim in claims:
                        yield ClaimMinted(claim)
                        if call.name == "lean_prove":
                            _lock_from_prove(session, call, claim, store)
                        if not self.config.hunt:
                            continue
                        if self.config.hunt_forever:
                            kind = campaign_settlement(
                                claim, call, verify_type=self._verify_bk_settlement
                            )
                            if kind is not None:
                                hunt_hit = True
                                hunt_settlement = kind
                        elif call.name == "lean_prove" and _is_hunt_proof(
                            claim,
                            require_durable=self.config.hunt_require_durable,
                        ):
                            hunt_hit = True
                else:
                    lit_hits = _literature_hits_from_result(result)
                    if lit_hits is not None:
                        turn_refs.extend(lit_hits)
                    else:
                        ax_hits = _arxiv_hits_from_result(result)
                        if ax_hits is not None:
                            turn_refs.extend(ax_hits)
                    rendered = _render_result(result)
                    tr = ToolResultMsg(id=call.id, content=rendered)
                    self._persist_item(session, tr, store)
                    yield ToolResult(call=call, content=rendered, is_error=False)

                if self._interrupt:
                    for rest in unanswered:
                        tr = ToolResultMsg(
                            id=rest.id,
                            content="ERROR Interrupted",
                            is_error=True,
                        )
                        self._persist_item(session, tr, store)
                        yield ToolResult(call=rest, content=tr.content, is_error=True)
                    yield Interrupted()
                    return

            if self.config.hunt and hunt_hit:
                commentary = _hunt_stop_commentary(hunt_settlement)
                grounded = format_grounded_answer(
                    commentary=commentary,
                    claims=turn_claims,
                    failures=turn_failures,
                    references=turn_refs,
                    definitions=turn_definitions,
                )
                yield AssistantFinal(
                    text=grounded,
                    commentary=commentary,
                    claims=tuple(turn_claims),
                    failures=tuple(turn_failures),
                    references=tuple(turn_refs),
                    definitions=tuple(turn_definitions),
                )
                return

        # Hit max_steps / hunt_max_rounds without a final text turn.
        return

    def run(
        self,
        task: str,
        *,
        session: Session | None = None,
        store: SessionStore | None = None,
    ) -> AgentResult:
        """Headless one-shot: seed a user message, drain ``step``, return result."""
        sess = session or Session.create()
        if store is not None and not store.path_for(sess.id).exists():
            store.create(sess)
        seed = (
            UserMsg(f"{task}\n\n{_hunt_kickoff_text(self.config)}")
            if self.config.hunt
            else _seed_user_message(task)
        )
        if store is not None:
            store.log_user(sess, seed.text)
        else:
            sess.history.append(seed)

        transcript: list[Observation] = []
        final: str | None = None
        commentary: str | None = None

        for event in self.step(sess, store=store):
            if isinstance(event, AssistantFinal):
                final = event.text
                commentary = event.commentary
            elif isinstance(event, ToolResult):
                transcript.append(
                    Observation(
                        event.call,
                        event.content,
                        is_error=event.is_error,
                        unavailable=event.unavailable,
                    )
                )
            elif isinstance(event, Interrupted):
                break

        self.ledger = sess.ledger
        return AgentResult(
            final=final,
            ledger=sess.ledger,
            steps=self._rounds,
            transcript=transcript,
            session=sess,
            commentary=commentary,
        )
