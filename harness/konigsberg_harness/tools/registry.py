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
    BkPredicateArgs,
    BkSearchArgs,
    ChoosabilityRefuteArgs,
    DecideColorableArgs,
    FixerBreakerArgs,
    Graph6Args,
    LeanCheckArgs,
    LeanProveArgs,
    LeanSearchArgs,
    LeanTypecheckStatementArgs,
    LiteratureSearchArgs,
    VerifyColoringArgs,
    schema_for,
)

if TYPE_CHECKING:
    from ..lean_repl import LeanREPL

# Re-export so callers/tests can catch the same class the loop catches.
__all__ = ["Tool", "ToolRegistry", "ValidationError", "build_registry"]


@dataclass
class Tool:
    name: str
    fn: Callable[..., Any]
    doc: str = ""
    args_model: type[BaseModel] | None = None


@dataclass
class ToolRegistry:
    _tools: dict[str, Tool] = field(default_factory=dict)

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


def build_registry(repl: LeanREPL | None = None) -> ToolRegistry:
    """Populate a registry with the real tools.

    Empirical tools need no Lean; the formal tools are bound to a live `repl`
    (via partial) and only registered when one is supplied — so a Lean-free
    session (e.g. pure counterexample search) still gets a working registry.
    Imports are deferred to keep import-time coupling low.

    `counterexample_search` is registered for code use but has no args_model, so
    it is omitted from `tool_specs()` (non-JSON-serializable predicate).
    """
    from . import empirical_tools as et
    from . import lean_tools as lt
    from . import literature_tools as lit

    reg = ToolRegistry()
    reg.register(
        "literature_search",
        lit.literature_search,
        "Search the in-repo Literature corpus (and EXTERNAL.toml). Returns "
        "status-bearing records (formalized / stated / external-verified); does "
        "NOT mint ledger Claims. Carry each hit's status verbatim — stated ≠ proven.",
        args_model=LiteratureSearchArgs,
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
        "certificate that the graph is NOT k-choosable. A hit is re-verified "
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
    reg.register(
        "bk_search",
        et.bk_search,
        "Principled Rabern-style BK candidate search: enumerate connected "
        "deg∈{3,4} graphs up to n_max, filter bad-K₂ / K4-free / k-colorable, "
        "test choice-criticality. NOT a Δ≥9 chromatic-tight search — see tool "
        "output LIMITS. Prefer this over inventing graph6 strings.",
        args_model=BkSearchArgs,
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
            "#print axioms. The only tool that can mint kernel-trust.",
            args_model=LeanProveArgs,
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
