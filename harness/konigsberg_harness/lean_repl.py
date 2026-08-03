"""Persistent Lean environment (LeanREPL-backed).

A persistent process, NOT a shell-out per snippet: keeps live elaboration state,
returns structured goal state, amortizes startup. This is a hard-to-change
contract (open decision #1) — evaluate LeanREPL vs alternatives before
committing.

Every call is isolated and TIMED. `decide` on a large SimpleGraph will hang; the
timeout is a correctness feature, not just hygiene.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GoalState:
    goals: list[str]
    errors: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


class LeanREPL:
    def __init__(self, project_dir: str = "formal", timeout_s: float = 20.0) -> None:
        self.project_dir = project_dir
        self.timeout_s = timeout_s

    def start(self) -> None:
        raise NotImplementedError("spawn persistent LeanREPL over project_dir")

    def send(self, snippet: str) -> GoalState:
        """Elaborate a snippet against live state; return goals + errors."""
        raise NotImplementedError

    def print_axioms(self, lean_name: str) -> list[str]:
        """`#print axioms {lean_name}` -> parsed axiom list. Used by check_axioms."""
        raise NotImplementedError

    def close(self) -> None:
        pass
