"""Counterexample search — the highest-ROI tool in the system.

Enumerate to a bound, test a predicate, return the first violation. Kills bad
conjectures before any formalization cost is incurred.

GUARD (empirical analogue of lean_typecheck_statement): a "no counterexample"
result is only as good as the predicate encoding. `validate_predicate` sanity-
checks the predicate against known-answer cases before a search is trusted, so a
mis-encoded conjecture cannot masquerade as verified.
"""
from __future__ import annotations

from collections.abc import Callable

from ..core import Graph
from .enumerate import all_graphs

Predicate = Callable[[Graph], bool]


def validate_predicate(predicate: Predicate, known_cases: list[tuple[Graph, bool]]) -> bool:
    """Return True iff the predicate matches every known (graph, expected) pair."""
    return all(predicate(g) is expected for g, expected in known_cases)


def first_violation(predicate: Predicate, bound: int) -> Graph | None:
    """First graph up to `bound` vertices where predicate is False, else None.

    The loop is real; it depends on enumerate.all_graphs, which is wired to
    nauty. Callers should validate_predicate first."""
    for n in range(1, bound + 1):
        for g in all_graphs(n):
            if not predicate(g):
                return g
    return None
