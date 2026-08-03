"""Ranked lemma/definition surfacing for the current goal state.

HONEST FRAMING (do not repeat the plan's "Aider domain-swapped" line): Aider
ranks source SYMBOLS by static reference count over a dependency graph — cheap,
purely structural. Ranking LEMMAS by applicability to a live goal state is
PREMISE SELECTION, a semantic, open research problem. It is NOT the same
architecture domain-swapped.

Consequence for v1: lean_search (exact?/apply?/Loogle) already IS a premise
selector. Start there. This module should be a cheap STRUCTURAL index
(namespace/dependency/def-use over the own library) that complements
lean_search, not a second, under-specified retrieval system competing with it.
Treat learned goal-conditioned ranking as a scoped research task with its own
eval, not a freebie.
"""
from __future__ import annotations


def structural_index(library_root: str) -> dict:
    """Cheap, deterministic index: namespaces, signatures, def-use edges."""
    raise NotImplementedError


def rank_for_goal(goal_state: str, token_budget: int) -> list[str]:
    """Premise selection. Research subproblem — see module docstring."""
    raise NotImplementedError
