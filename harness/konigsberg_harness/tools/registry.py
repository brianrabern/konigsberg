"""Tool registration + dispatch. Minimal and real: a name -> callable table.

Model-callable tools carry a pydantic `args_model` that both generates the API
`input_schema` and validates args before the underlying function runs.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from functools import partial
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ValidationError

from .arg_models import (
    AlonTarsiArgs,
    ArxivSearchArgs,
    BkPredicateArgs,
    BkSearchArgs,
    ChoosabilityRefuteArgs,
    DecideColorableArgs,
    DischargingArgs,
    EmptyArgs,
    FixerBreakerArgs,
    Graph6Args,
    LeanAddToLibraryArgs,
    LeanCheckArgs,
    LeanProveArgs,
    LeanRetractArgs,
    LeanSearchArgs,
    LeanTypecheckStatementArgs,
    LemmaReadArgs,
    ListCriticalArgs,
    LiteratureSearchArgs,
    ReducibleConfigurationArgs,
    ReedSweepArgs,
    VerifyColoringArgs,
    schema_for,
)
from .fundamentals_tools import CATEGORY_ORDER, category_for, register_fundamentals

if TYPE_CHECKING:
    from ..lean_repl import LeanREPL
    from ..lemmas import LemmaNotebook

# Re-export so callers/tests can catch the same class the loop catches.
__all__ = [
    "CATEGORY_ORDER",
    "Tool",
    "ToolRegistry",
    "ValidationError",
    "build_registry",
    "category_for",
]


@dataclass
class Tool:
    name: str
    fn: Callable[..., Any]
    doc: str = ""
    args_model: type[BaseModel] | None = None


@dataclass
class ToolRegistry:
    _tools: dict[str, Tool] = field(default_factory=dict)
    campaign_bind: Any = None

    def register(
        self,
        name: str,
        fn: Callable[..., Any],
        doc: str = "",
        args_model: type[BaseModel] | None = None,
    ) -> None:
        if name in self._tools:
            raise ValueError(f"tool already registered: {name}")
        self._tools[name] = Tool(name, fn, doc or (fn.__doc__ or ""), args_model)

    def dispatch(self, name: str, args: dict | None = None, **kwargs: Any) -> Any:
        """Run a tool. Prefer `args` dict (agent path); `**kwargs` kept for tests/code."""
        if name not in self._tools:
            raise KeyError(f"unknown tool: {name}")
        tool = self._tools[name]
        payload = dict(args) if args is not None else dict(kwargs)
        if tool.args_model is not None:
            validated = tool.args_model.model_validate(payload)
            payload = validated.model_dump()
        return tool.fn(**payload)

    def tool_specs(self) -> list[dict]:
        """Anthropic-shaped tool list: only tools with an args_model (model-callable)."""
        out: list[dict] = []
        for t in self._tools.values():
            if t.args_model is None:
                continue  # code-only (e.g. counterexample_search)
            out.append(
                {
                    "name": t.name,
                    "description": t.doc,
                    "input_schema": schema_for(t.args_model),
                }
            )
        return out

    def spec(self) -> list[dict[str, str]]:
        """Legacy name/doc list (all registered tools). Prefer `tool_specs` for the API."""
        return [{"name": t.name, "doc": t.doc} for t in self._tools.values()]

    def names(self) -> list[str]:
        return list(self._tools)

    def grouped_tool_specs(self) -> list[tuple[str, list[dict]]]:
        """Model-callable tools grouped by category for ``/tools`` display."""
        buckets: dict[str, list[dict]] = {c: [] for c in CATEGORY_ORDER}
        for spec in self.tool_specs():
            cat = category_for(spec["name"])
            buckets.setdefault(cat, []).append(spec)
        return [(c, buckets[c]) for c in CATEGORY_ORDER if buckets.get(c)]


def build_registry(
    repl: LeanREPL | None = None,
    notebook: LemmaNotebook | None = None,
) -> ToolRegistry:
    """Populate a registry with the real tools.

    Empirical tools need no Lean; the formal tools are bound to a live `repl`
    (via partial) and only registered when one is supplied — so a Lean-free
    session (e.g. pure counterexample search) still gets a working registry.
    Imports are deferred to keep import-time coupling low.

    `counterexample_search` is registered for code use but has no args_model, so
    it is omitted from `tool_specs()` (non-JSON-serializable predicate).
    """
    from ..campaign import CampaignBind, campaign_status
    from ..lemmas import LemmaNotebook, lemma_list, lemma_read
    from . import arxiv_tools as ax
    from . import empirical_tools as et
    from . import lean_tools as lt
    from . import literature_tools as lit

    if repl is not None and notebook is None:
        notebook = LemmaNotebook()

    reg = ToolRegistry()
    register_fundamentals(reg)
    reg.register(
        "literature_search",
        lit.literature_search,
        "Search the in-repo Literature corpus (and EXTERNAL.toml). Returns "
        "status-bearing records (formalized / stated / external-verified); does "
        "NOT mint ledger Claims. Carry each hit's status verbatim — stated ≠ proven.",
        args_model=LiteratureSearchArgs,
    )
    reg.register(
        "arxiv_search",
        ax.arxiv_search,
        "Search arXiv (default cat:math.CO). Returns bibliographic hits "
        "(title, authors, abs url, summary snippet) with status=arxiv. Does NOT "
        "mint ledger Claims and does NOT verify the papers — use for leads, then "
        "prefer literature_search / Lean / empirical tools to establish anything. "
        "Pass category=null for unfiltered search.",
        args_model=ArxivSearchArgs,
    )
    reg.register(
        "counterexample_search",
        et.counterexample_search,
        "Enumerate graphs up to a bound and return the first predicate violation "
        "(or a positive result if none); mints a python-checked Claim.",
        # no args_model — code-only
    )
    reg.register(
        "choosability_refute",
        et.choosability_refute,
        "Given a graph6 string, k, and optional palette: search (CEGAR/SAT) for a "
        "certificate that the graph is NOT k-choosable. Live hunt caps n≤6 and "
        "~45s (KONIGSBERG_CHOOSABILITY_MAX_N / _TIMEOUT); listed cores / "
        "H??F~~~ are already on 𝒞 — do not re-SAT them. A hit is re-verified "
        "(certificate-checked); a miss at the default palette decides k-choosable "
        "(python-checked).",
        args_model=ChoosabilityRefuteArgs,
    )
    reg.register(
        "alon_tarsi",
        et.alon_tarsi,
        "Given a graph6 string: search for an Alon–Tarsi orientation certificate "
        "(sufficient for list-colorability). A hit is independently re-checked "
        "(certificate-checked). A miss proves nothing — AT is sufficient only.",
        args_model=AlonTarsiArgs,
    )
    reg.register(
        "reducible_configuration",
        et.reducible_configuration,
        "Test BK reducibility of a local configuration (core graph6 + ambient "
        "degrees, optional D). f-choosability of the core is SUFFICIENT for "
        "reducibility, not necessary — a miss proves nothing, exactly like "
        "alon_tarsi. Live hunt caps n≤6 and ~45s — do not retest listed cores. "
        "Requires H_BK (Δ=D≥9, K_D-free, D-critical). The "
        "bridge BK.reducible_of_fChoosable is formalized; a HIT is still "
        "sufficient-only. HIT mints a forbidden-config Claim; MISS "
        "mints nothing and proves nothing.",
        args_model=ReducibleConfigurationArgs,
    )
    bind = CampaignBind()
    reg.campaign_bind = bind
    reg.register(
        "discharging_unavoidable",
        partial(et.discharging_unavoidable, bind),
        "Verify a proposed discharging argument (μ + rules + forbidden cores) "
        "at Δ = D. v1 is D=9 only. UNAVOIDABLE is SUFFICIENT for the discharging "
        "half — a miss returns surviving neighborhood types and proves nothing. "
        "Forbidden cores must already be minted reducible "
        "on the ledger. HIT is conditional on "
        "BK.reducible_and_unavoidable_imp_no_counterexample.",
        args_model=DischargingArgs,
    )
    reg.register(
        "campaign_status",
        partial(campaign_status, bind),
        "Ledger-backed BK staircase: |𝒞|, locked lemmas, discharging "
        "(closed / last miss neighborhood), and the first incomplete increment. "
        "Does NOT mint a Claim. Call this instead of rediscovering C4/C6. "
        "NEXT is the only assigned work. A frozen stair surfaces REFORMULATE "
        "(Rabern: equivalent weaker-looking form).",
        args_model=EmptyArgs,
    )
    reg.register(
        "fixer_breaker",
        et.fixer_breaker,
        "Given a graph6 string and per-vertex list sizes: decide the online "
        "choosability (paintability) fixer-breaker game. Returns solver-certified "
        "(fingerprint-validated port; strategy certificate is a stretch goal).",
        args_model=FixerBreakerArgs,
    )
    reg.register(
        "decide_colorable",
        et.decide_colorable,
        "Given graph6 and k: decide ordinary proper k-colorability (not choosability). "
        "If colorable, returns a witness coloring (certificate-checked); pass that "
        "witness to verify_coloring to upgrade to a kernel-proved Claim. If not, "
        "mints a not-k-colorable Claim (certificate-checked on a clique/odd-cycle "
        "obstruction when extractable, else python-checked at SAT completeness).",
        args_model=DecideColorableArgs,
    )
    reg.register(
        "max_degree",
        et.max_degree,
        "Given graph6: compute Δ(G) with the degree sequence. python-checked.",
        args_model=Graph6Args,
    )
    reg.register(
        "clique_number",
        et.clique_number,
        "Given graph6: compute ω(G) with a witnessing clique (re-checked). "
        "certificate-checked.",
        args_model=Graph6Args,
    )
    reg.register(
        "chromatic_number",
        et.chromatic_number,
        "Given graph6: compute χ(G) searching up from ω. Returns a χ-coloring "
        "(upper; upgrade via verify_coloring) and not-(χ−1) evidence (lower). "
        "Ordinary chromatic number — not choosability.",
        args_model=Graph6Args,
    )
    _bk_pred = (
        partial(et.bk_predicate, repl=repl) if repl is not None else et.bk_predicate
    )
    reg.register(
        "bk_predicate",
        _bk_pred,
        "Evaluate Borodin–Kostochka on graph6: hypothesis Δ≥9; claims "
        "χ ≤ max{ω, Δ−1}. Returns hypothesis-not-met / satisfies / VIOLATES with "
        "Δ/ω/χ certificates. Ordinary chromatic BK — not choosability. "
        "On a violation (and Lean available), also kernel-upgrades the χ-coloring.",
        args_model=BkPredicateArgs,
    )
    _reed_pred = (
        partial(et.reed_predicate, repl=repl) if repl is not None else et.reed_predicate
    )
    reg.register(
        "reed_predicate",
        _reed_pred,
        "Evaluate Reed's conjecture on graph6 (open; claimed for all graphs): "
        "χ ≤ ⌈(Δ+ω+1)/2⌉. Returns satisfies / VIOLATES with Δ/ω/χ certificates and "
        "a tight-case flag (χ = the bound). Ordinary chromatic Reed. On a violation "
        "(and Lean available), also kernel-upgrades the χ-coloring.",
        args_model=Graph6Args,
    )
    reg.register(
        "reed_sweep",
        et.reed_sweep,
        "Census: verify Reed's bound χ ≤ ⌈(Δ+ω+1)/2⌉ over ALL graphs on "
        "n_min..n_max vertices in one pass (geng, or atlas for n≤7). Mints ONE "
        "summary Claim: count checked, all-satisfy / first-violation, and the "
        "tight-case census (χ = bound). Use this for a sweep — do NOT loop "
        "reed_predicate by hand over an enumeration.",
        args_model=ReedSweepArgs,
    )
    reg.register(
        "bk_search",
        et.bk_search,
        "Principled Rabern-style BK candidate search: enumerate connected "
        "deg∈{3,4} graphs up to n_max, filter bad-K₂ / K4-free / k-colorable, "
        "test choice-criticality. NOT a Δ≥9 chromatic-tight search — see tool "
        "output LIMITS. Prefer this over inventing graph6 strings.",
        args_model=BkSearchArgs,
    )
    reg.register(
        "list_critical",
        et.list_critical,
        "Decide whether graph6 is m-list-critical (Cranston–Rabern index baked "
        "in: not (m−1)-choosable + edge-minimal; Lean KListCritical/"
        "EdgeKListCritical). Internally is_choice_critical(G, m-1). For "
        "'is G k-list-critical' call this — do NOT reassemble from "
        "choosability_refute with a guessed k.",
        args_model=ListCriticalArgs,
    )
    if notebook is not None:
        reg.register(
            "lemma_list",
            partial(lemma_list, notebook),
            "List lemmas/theorems locked this investigation (name + durable/"
            "session tag). Read a snippet with lemma_read. These survive "
            "--resume and are replayed into Lean; they are not Literature "
            "until /promote.",
            args_model=EmptyArgs,
        )
        reg.register(
            "lemma_read",
            partial(lemma_read, notebook),
            "Return the locked Lean snippet for a named lemma from this "
            "session's working notebook.",
            args_model=LemmaReadArgs,
        )
    if repl is not None:
        from . import bridge as br

        reg.register(
            "lean_check",
            partial(lt.lean_check, repl),
            "Typecheck a Lean snippet against the live env; returns goal state + errors.",
            args_model=LeanCheckArgs,
        )
        reg.register(
            "lean_typecheck_statement",
            partial(lt.lean_typecheck_statement, repl),
            "Check a statement elaborates as a proposition; mints a `stated` Claim.",
            args_model=LeanTypecheckStatementArgs,
        )
        reg.register(
            "lean_search",
            partial(lt.lean_search, repl),
            "exact?/apply? search for lemmas bearing on a goal; returns candidate "
            "tactics (not verified — run them through lean_prove).",
            args_model=LeanSearchArgs,
        )
        reg.register(
            "lean_prove",
            partial(lt.lean_prove, repl),
            "Elaborate a full proof; on success mints a `proved` Claim carrying "
            "#print axioms. The only tool that can mint kernel-trust. "
            "Do not `import` Mathlib/Konigsberg — the scratch env already loaded "
            "them (imports are stripped, then illegal). A compile miss is not a "
            "proof; rewrite the snippet or abandon the lemma. "
            "Pass durable=True to elaborate against a fresh corpus env (no session "
            "decls) — required for promotability. Session-only proofs are tagged "
            "[session-only] and lean_add_to_library refuses them. Every success "
            "is locked on the working notebook (lemma_list / lemma_read) and "
            "installed in the session env. Unit of durable work: one self-contained "
            "snippet (helpers + target), not a pile of env lemmas.",
            args_model=LeanProveArgs,
        )
        reg.register(
            "reset_env",
            partial(lt.reset_env, repl, notebook),
            "Drop ephemeral session Lean declarations, reload the corpus "
            "preamble, then replay locked lemmas from the working notebook.",
            args_model=EmptyArgs,
        )
        reg.register(
            "retract",
            partial(lt.retract, repl),
            "Drop a single named session declaration and rebuild the remaining "
            "session cmds from the corpus preamble.",
            args_model=LeanRetractArgs,
        )
        reg.register(
            "lean_add_to_library",
            partial(lt.lean_add_to_library, repl),
            "Promote a referee-accepted proved result into Literature (write-back). "
            "REFUSES without durable=True provenance, an accepting referee_report, "
            "clean axioms, SanityChecks, and human confirmation "
            "(confirmed=True from /promote only). "
            "Do not call this from ordinary research turns — use /promote.",
            args_model=LeanAddToLibraryArgs,
        )
        reg.register(
            "verify_coloring",
            partial(br.verify_coloring, repl=repl),
            "Given graph6 and a concrete coloring (list of ℕ, one per vertex): "
            "re-check that coloring is proper in the Lean kernel via decide; "
            "mints a `proved` Claim. Does not decide Colorable k.",
            args_model=VerifyColoringArgs,
        )
    return reg
