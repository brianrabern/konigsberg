"""Formal-tier tools that don't need a live Lean env: the search-suggestion
parser (tested on realistic exact?/apply? output) plus lean_search,
lean_typecheck_statement, and lean_prove compile-miss handling via a stub REPL.

lean_prove / real elaboration are covered by the live smoke test + CI lean job.
"""
import pytest
from konigsberg_harness.lean_repl import GoalState, LeanREPLError
from konigsberg_harness.ledger import EvidenceKind, TrustRoot
from konigsberg_harness.tools.lean_tools import (
    _parse_suggestions,
    format_compile_miss,
    lean_prove,
    lean_search,
    lean_typecheck_statement,
    strip_repl_imports,
)


class StubREPL:
    """Returns a fixed GoalState and records the last snippet it was sent."""

    def __init__(self, gs: GoalState, *, axioms=None, axioms_error: str | None = None):
        self._gs = gs
        self.last: str | None = None
        self._axioms = list(axioms) if axioms is not None else ["propext"]
        self._axioms_error = axioms_error

    def ensure_preamble(self, preamble=None, *, timeout_s=None) -> None:
        return None

    def load_preamble(self, preamble=None, *, timeout_s=None) -> None:
        return None

    def snapshot(self):
        return {}

    def restore(self, _snap) -> None:
        return None

    def send(self, snippet, *, timeout_s=None, new_env=False, commit=True) -> GoalState:
        self.last = snippet
        return self._gs

    def send_transactional(self, snippet, *, timeout_s=None) -> GoalState:
        return self.send(snippet, timeout_s=timeout_s, commit=True)

    def print_axioms(self, _name, *, timeout_s=None):
        if self._axioms_error:
            raise LeanREPLError(self._axioms_error)
        return list(self._axioms)


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


# --- lean_prove compile misses --------------------------------------------


def test_strip_repl_imports_drops_leading_and_mid_file_imports():
    body, stripped = strip_repl_imports(
        "import Mathlib\nimport Konigsberg\n\ntheorem foo : True := trivial\n"
    )
    assert "import" not in body
    assert "theorem foo" in body
    assert any("Mathlib" in s for s in stripped)


def test_format_compile_miss_is_short_and_actionable():
    msg = format_compile_miss(
        "foo",
        ["invalid 'import' command, it must be used in the beginning of the file"],
        stripped_imports=["import Mathlib"],
    )
    assert msg.startswith("LEAN COMPILE MISS")
    assert "not a kernel proof" in msg
    assert "do not resubmit" in msg.lower() or "Do not resubmit" in msg
    assert "Dropped illegal" in msg


def test_lean_prove_strips_imports_before_send():
    stub = StubREPL(GoalState(goals=[], errors=[], infos=[]))
    claim = lean_prove(
        stub,
        "foo",
        "import Mathlib\nimport Konigsberg\ntheorem foo : True := trivial",
    )
    assert "import" not in (stub.last or "")
    assert "theorem foo" in (stub.last or "")
    assert claim.provenance.label() == "proved"


def test_lean_prove_compile_miss_does_not_mint():
    stub = StubREPL(GoalState(goals=[], errors=["unknown identifier 'bar'"], infos=[]))
    with pytest.raises(ValueError, match="LEAN COMPILE MISS"):
        lean_prove(stub, "foo", "theorem foo : bar := trivial")


def test_lean_prove_import_only_snippet_is_a_miss():
    stub = StubREPL(GoalState(goals=[], errors=[], infos=[]))
    with pytest.raises(ValueError, match="only `import`"):
        lean_prove(stub, "foo", "import Mathlib\nimport Konigsberg\n")


def test_lean_prove_unknown_decl_after_ok_elaboration():
    stub = StubREPL(
        GoalState(goals=[], errors=[], infos=[]),
        axioms_error="#print axioms foo failed: Unknown constant `foo`",
    )
    with pytest.raises(ValueError, match="not in the env"):
        lean_prove(stub, "foo", "namespace Hidden\ntheorem foo : True := trivial\nend Hidden")


def test_lean_prove_sorry_is_a_compile_miss():
    stub = StubREPL(
        GoalState(goals=[], errors=[], infos=[]),
        axioms=["propext", "sorryAx"],
    )
    with pytest.raises(ValueError, match="sorryAx"):
        lean_prove(stub, "foo", "theorem foo : True := by\n  admit")
