"""Formal-tier tools. Each returns a ledger Claim with a LEAN_KERNEL trust root.

    lean_check              typecheck against live env; goal state + errors
    lean_typecheck_statement statement well-formedness w/o proof
                             (catches "proved the wrong thing")
    lean_eval               #eval / #reduce; decidable computation in Lean
    lean_search             exact?/apply?/Loogle over mathlib + own library
    lean_add_to_library     GATED commit of an accepted lemma (behind check_axioms)
"""
from __future__ import annotations

import re

from ..lean_repl import GoalState, LeanREPL
from ..ledger import Claim, mint_lean_proof, mint_lean_statement

_SEARCH_TACTICS = ("exact?", "apply?")

# `exact?`/`apply?` print candidates as "Try this: <tactic>" (singular) or a
# "Try these:" header followed by • / · bulleted tactics.
_SUGGESTION = re.compile(r"Try (?:this|these):\s*(.*)")
_BULLET = re.compile(r"^\s*[•·]\s*(.+)$")


def _parse_suggestions(text: str) -> list[str]:
    """Extract suggested tactic snippets from search-tactic output, in order."""
    out: list[str] = []
    for line in text.splitlines():
        m = _SUGGESTION.search(line)
        if m:
            snippet = m.group(1).strip()
            if snippet:  # "Try these:" header carries no snippet itself
                out.append(snippet)
            continue
        b = _BULLET.match(line)
        if b:
            out.append(b.group(1).strip())
    seen: set[str] = set()
    return [s for s in out if not (s in seen or seen.add(s))]


def lean_check(repl: LeanREPL, snippet: str) -> GoalState:
    repl.ensure_preamble()
    return repl.send(snippet)


def lean_typecheck_statement(
    repl: LeanREPL, statement: str, *, timeout_s: float | None = None
) -> Claim:
    """Well-formed-only: the statement elaborates (as a proposition). Says NOTHING
    about truth. Its job is to catch "proved the wrong thing" — a statement that
    doesn't even parse/elaborate — before any proof effort is spent. Raises if the
    statement fails to elaborate; otherwise mints a `stated` Claim.
    """
    repl.ensure_preamble(timeout_s=timeout_s)
    state = repl.send(f"example : {statement} := sorry", timeout_s=timeout_s)
    if not state.ok:
        raise ValueError(f"statement does not elaborate: {state.errors}")
    return mint_lean_statement(statement, tool="lean_typecheck_statement")


def lean_prove(repl: LeanREPL, lean_name: str, snippet: str) -> Claim:
    """Elaborate a full proof; on success mint a proof Claim carrying #print axioms."""
    repl.ensure_preamble()
    state = repl.send(snippet)
    if not state.ok:
        raise ValueError(f"proof failed: {state.errors}")
    axioms = tuple(repl.print_axioms(lean_name))
    return mint_lean_proof(statement=lean_name, axioms=axioms, tool="lean_prove")


def lean_search(
    repl: LeanREPL, goal: str, *, tactic: str = "exact?", timeout_s: float | None = None
) -> list[str]:
    """Search mathlib + the own library for lemmas bearing on `goal`.

    Runs `example : <goal> := by <tactic>` (tactic in exact?/apply?) and returns
    the tactic snippets the search suggests, e.g. "exact Foo.bar". These are
    CANDIDATES, not verified facts: a suggestion is only trustworthy once run and
    typechecked (via lean_prove). Hence this returns plain strings and mints no
    Claim. Returns [] when the search finds nothing.
    """
    if tactic not in _SEARCH_TACTICS:
        raise ValueError(f"tactic must be one of {_SEARCH_TACTICS}, got {tactic!r}")
    repl.ensure_preamble(timeout_s=timeout_s)
    state = repl.send(f"example : {goal} := by {tactic}", timeout_s=timeout_s)
    return _parse_suggestions("\n".join([*state.infos, *state.errors]))


def lean_add_to_library(repl: LeanREPL, lean_name: str, snippet: str) -> Claim:
    """Commit only after the axiom gate accepts. Never automatic."""
    raise NotImplementedError
