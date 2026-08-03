"""Tool registration + dispatch. Minimal and real: a name -> callable table."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


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
