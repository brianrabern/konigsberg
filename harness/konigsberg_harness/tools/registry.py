"""Tool registration + dispatch. Minimal and real: a name -> callable table."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from functools import partial
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..lean_repl import LeanREPL


@dataclass
class Tool:
    name: str
    fn: Callable[..., Any]
    doc: str = ""


@dataclass
class ToolRegistry:
    _tools: dict[str, Tool] = field(default_factory=dict)

    def register(self, name: str, fn: Callable[..., Any], doc: str = "") -> None:
        if name in self._tools:
            raise ValueError(f"tool already registered: {name}")
        self._tools[name] = Tool(name, fn, doc or (fn.__doc__ or ""))

    def dispatch(self, name: str, **kwargs: Any) -> Any:
        if name not in self._tools:
            raise KeyError(f"unknown tool: {name}")
        return self._tools[name].fn(**kwargs)

    def spec(self) -> list[dict[str, str]]:
        """Serializable tool list to hand the model."""
        return [{"name": t.name, "doc": t.doc} for t in self._tools.values()]

    def names(self) -> list[str]:
        return list(self._tools)


def build_registry(repl: LeanREPL | None = None) -> ToolRegistry:
    """Populate a registry with the real tools.

    Empirical tools need no Lean; the formal tools are bound to a live `repl`
    (via partial) and only registered when one is supplied — so a Lean-free
    session (e.g. pure counterexample search) still gets a working registry.
    Imports are deferred to keep import-time coupling low.
    """
    from . import empirical_tools as et
    from . import lean_tools as lt

    reg = ToolRegistry()
    reg.register(
        "counterexample_search",
        et.counterexample_search,
        "Enumerate graphs up to a bound and return the first predicate violation "
        "(or a positive result if none); mints a python-checked Claim.",
    )
    if repl is not None:
        reg.register(
            "lean_check",
            partial(lt.lean_check, repl),
            "Typecheck a Lean snippet against the live env; returns goal state + errors.",
        )
        reg.register(
            "lean_typecheck_statement",
            partial(lt.lean_typecheck_statement, repl),
            "Check a statement elaborates as a proposition; mints a `stated` Claim.",
        )
        reg.register(
            "lean_search",
            partial(lt.lean_search, repl),
            "exact?/apply? search for lemmas bearing on a goal; returns candidate "
            "tactics (not verified — run them through lean_prove).",
        )
        reg.register(
            "lean_prove",
            partial(lt.lean_prove, repl),
            "Elaborate a full proof; on success mints a `proved` Claim carrying "
            "#print axioms. The only tool that can mint kernel-trust.",
        )
    return reg
