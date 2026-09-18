"""Formal-tier tools that don't need a live Lean env: the search-suggestion
parser (tested on realistic exact?/apply? output) plus lean_search and
lean_typecheck_statement driven through a stub REPL.

lean_prove / real elaboration are covered by the live smoke test + CI lean job.
"""
import pytest
from konigsberg_harness.lean_repl import GoalState
from konigsberg_harness.ledger import EvidenceKind, TrustRoot
from konigsberg_harness.tools.lean_tools import (
    _parse_suggestions,
    lean_search,
    lean_typecheck_statement,
)


class StubREPL:
    """Returns a fixed GoalState and records the last snippet it was sent."""

    def __init__(self, gs: GoalState):
        self._gs = gs
        self.last: str | None = None

    def ensure_preamble(self, preamble=None, *, timeout_s=None) -> None:
        return None

    def send(self, snippet, *, timeout_s=None, new_env=False, commit=True) -> GoalState:
        self.last = snippet
        return self._gs

    def send_transactional(self, snippet, *, timeout_s=None) -> GoalState:
        return self.send(snippet, timeout_s=timeout_s, commit=True)


# --- _parse_suggestions ---------------------------------------------------

def test_parse_single_try_this():
    assert _parse_suggestions("Try this: exact Nat.add_comm") == ["exact Nat.add_comm"]


def test_parse_multiple_try_this_lines():
    text = "Try this: exact foo\nsome noise\nTry this: apply bar"
    assert _parse_suggestions(text) == ["exact foo", "apply bar"]


def test_parse_try_these_bulleted_block():
    text = "Try these:\n• exact foo\n• exact bar"
    assert _parse_suggestions(text) == ["exact foo", "exact bar"]


def test_parse_dedupes_preserving_order():
    text = "Try this: exact foo\nTry this: exact foo\nTry this: exact baz"
    assert _parse_suggestions(text) == ["exact foo", "exact baz"]


def test_parse_returns_empty_when_no_suggestions():
    assert _parse_suggestions("exact?: could not close the goal") == []


# --- lean_search ----------------------------------------------------------

def test_lean_search_parses_suggestions_and_builds_snippet():
    stub = StubREPL(GoalState(goals=[], errors=[], infos=["Try this: exact Nat.le_refl"]))
    out = lean_search(stub, "n <= n")
    assert out == ["exact Nat.le_refl"]
    assert stub.last == "example : n <= n := by exact?"


def test_lean_search_uses_requested_tactic():
    stub = StubREPL(GoalState(goals=[], errors=[], infos=[]))
    lean_search(stub, "p", tactic="apply?")
    assert stub.last == "example : p := by apply?"


def test_lean_search_reads_suggestions_from_errors_too():
    # exact? reports its "Try this" via a non-info message in some versions
    stub = StubREPL(GoalState(goals=[], errors=["Try this: exact h"], infos=[]))
    assert lean_search(stub, "q") == ["exact h"]


def test_lean_search_empty_when_nothing_found():
    stub = StubREPL(GoalState(goals=[], errors=["could not close"], infos=[]))
    assert lean_search(stub, "q") == []


def test_lean_search_rejects_unknown_tactic():
    stub = StubREPL(GoalState(goals=[], errors=[], infos=[]))
    with pytest.raises(ValueError):
        lean_search(stub, "q", tactic="rw?")


# --- lean_typecheck_statement ---------------------------------------------

def test_typecheck_statement_mints_stated_claim_on_success():
    # sorry warning only -> ok; well-formed statement
    stub = StubREPL(GoalState(goals=[], errors=[], infos=["declaration uses 'sorry'"]))
    claim = lean_typecheck_statement(stub, "forall n : Nat, n + 0 = n")
    assert claim.provenance.label() == "stated"
    assert claim.provenance.trust_root is TrustRoot.LEAN_KERNEL
    assert claim.provenance.evidence_kind is EvidenceKind.WELL_FORMED_ONLY
    assert stub.last == "example : forall n : Nat, n + 0 = n := sorry"


def test_typecheck_statement_raises_on_elaboration_error():
    stub = StubREPL(GoalState(goals=[], errors=["unknown identifier 'foo'"], infos=[]))
    with pytest.raises(ValueError):
        lean_typecheck_statement(stub, "foo n")
