"""Tool-layer errors with presentation semantics for the REPL."""
from __future__ import annotations


class ToolUnavailable(Exception):
    """A registered tool cannot run (missing runtime dependency, etc.).

    Distinct from an ordinary tool failure: the REPL surfaces this as a loud
    banner so neither the user nor the model can treat it as a normal result.
    """

    def __init__(self, tool: str, reason: str) -> None:
        self.tool = tool
        self.reason = reason
        super().__init__(f"TOOL UNAVAILABLE: {tool} — {reason}")

    def banner(self) -> str:
        return str(self)


class ToolBudgetExceeded(Exception):
    """A tool refused to run because inputs exceed safe computational bounds."""

    def __init__(self, tool: str, reason: str) -> None:
        self.tool = tool
        self.reason = reason
        super().__init__(f"TOOL BUDGET EXCEEDED: {tool} — {reason}")

    def banner(self) -> str:
        return str(self)
