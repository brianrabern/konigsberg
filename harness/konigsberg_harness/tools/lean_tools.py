"""Formal-tier tools. Each returns a ledger Claim with a LEAN_KERNEL trust root.

    lean_check              typecheck against live env; goal state + errors
    lean_typecheck_statement statement well-formedness w/o proof
                             (catches "proved the wrong thing")
    lean_eval               #eval / #reduce; decidable computation in Lean
    lean_search             exact?/apply?/Loogle over mathlib + own library
    lean_add_to_library     GATED commit of an accepted lemma (behind check_axioms)
"""
from __future__ import annotations

from ..ledger import Claim, mint_lean_proof, mint_lean_statement
from ..lean_repl import GoalState, LeanREPL


def lean_check(repl: LeanREPL, snippet: str) -> GoalState:
    return repl.send(snippet)


def lean_typecheck_statement(repl: LeanREPL, statement: str) -> Claim:
    """Well-formed-only: the statement elaborates as a Prop. Says nothing about truth."""
    raise NotImplementedError


def lean_prove(repl: LeanREPL, lean_name: str, snippet: str) -> Claim:
    """Elaborate a full proof; on success mint a proof Claim carrying #print axioms."""
    state = repl.send(snippet)
    if not state.ok:
        raise ValueError(f"proof failed: {state.errors}")
    axioms = tuple(repl.print_axioms(lean_name))
    return mint_lean_proof(statement=lean_name, axioms=axioms, tool="lean_prove")


def lean_search(repl: LeanREPL, query: str) -> list[str]:
    raise NotImplementedError


def lean_add_to_library(repl: LeanREPL, lean_name: str, snippet: str) -> Claim:
    """Commit only after the axiom gate accepts. Never automatic."""
    raise NotImplementedError
