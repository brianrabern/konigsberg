"""lean_repl: pure parsing + process-I/O behavior, no Lean toolchain required.

The parsing helpers (`_parse_axioms`, `_to_goal_state`) are unit-tested directly.
The subprocess machinery (framing, env threading, timeout-kill) is exercised with
a tiny fake REPL written in Python, so CI validates the I/O contract without a
built `formal/`.
"""
import sys
import time

import pytest
from konigsberg_harness.lean_repl import (
    GoalState,
    LeanREPL,
    LeanREPLError,
    LeanREPLTimeout,
    _parse_axioms,
    _to_goal_state,
)

# A fake REPL: read requests (blank-line framed), reply with one framed JSON
# object per request, always flushing. Echoes the received cmd and stamps env=0
# so env-threading is observable.
FAKE_REPL = r"""
import sys, json
buf = ""
for line in sys.stdin:
    if line.strip() == "":
        if buf.strip():
            obj = json.loads(buf)
            print(json.dumps({"env": 0, "echo": obj.get("cmd"),
                              "messages": [], "sorries": []}), flush=True)
            print(flush=True)
            buf = ""
    else:
        buf += line
"""


# --- _parse_axioms --------------------------------------------------------

def test_parse_axioms_none():
    assert _parse_axioms("'Foo.bar' does not depend on any axioms") == []


def test_parse_axioms_whitelisted_list():
    text = "'Foo.bar' depends on axioms: [propext, Classical.choice, Quot.sound]"
    assert _parse_axioms(text) == ["propext", "Classical.choice", "Quot.sound"]


def test_parse_axioms_catches_sorry_and_native_decide():
    # sorryAx = unfinished proof; Lean.ofReduceBool = native_decide. The gate,
    # not the parser, rejects these — the parser must SURFACE them faithfully.
    assert "sorryAx" in _parse_axioms("f depends on axioms: [sorryAx, propext]")
    assert "Lean.ofReduceBool" in _parse_axioms(
        "g depends on axioms: [Lean.ofReduceBool]"
    )


def test_parse_axioms_multiline_and_no_bracket_fallback():
    assert _parse_axioms("depends on axioms: [propext,\n Quot.sound]") == [
        "propext",
        "Quot.sound",
    ]
    assert _parse_axioms("x depends on axioms: propext Classical.choice") == [
        "propext",
        "Classical.choice",
    ]


# --- _to_goal_state -------------------------------------------------------

def test_to_goal_state_errors_and_infos_split_by_severity():
    resp = {
        "env": 3,
        "messages": [
            {"severity": "error", "data": "type mismatch"},
            {"severity": "info", "data": "some info"},
            {"severity": "warning", "data": "unused"},
        ],
    }
    gs = _to_goal_state(resp)
    assert gs.errors == ["type mismatch"]
    assert gs.infos == ["some info"]
    assert gs.env == 3
    assert gs.ok is False


def test_to_goal_state_goals_come_from_sorries_when_no_tactic_goals():
    resp = {"sorries": [{"goal": "⊢ True", "proofState": 0}], "messages": []}
    assert _to_goal_state(resp).goals == ["⊢ True"]


def test_to_goal_state_prefers_explicit_tactic_goals():
    resp = {"goals": ["⊢ P"], "sorries": [{"goal": "ignored"}], "messages": []}
    assert _to_goal_state(resp).goals == ["⊢ P"]


def test_to_goal_state_clean_result_is_ok():
    gs = _to_goal_state({"env": 0, "messages": []})
    assert gs.ok is True
    assert gs.goals == [] and gs.errors == []


# --- subprocess behavior (fake REPL) --------------------------------------

def test_send_roundtrips_and_threads_env():
    with LeanREPL(repl_cmd=[sys.executable, "-c", FAKE_REPL], timeout_s=5) as repl:
        gs = repl.send("theorem foo : True := trivial")
        assert gs.raw["echo"] == "theorem foo : True := trivial"
        assert gs.env == 0
        assert repl._env == 0  # threaded onto the instance for the next call
        gs2 = repl.send("theorem bar : True := trivial")
        assert gs2.raw["echo"] == "theorem bar : True := trivial"


def test_timeout_kills_the_process():
    repl = LeanREPL(
        repl_cmd=[sys.executable, "-c", "import time; time.sleep(30)"],
        timeout_s=0.3,
    )
    repl.start()
    t0 = time.monotonic()
    with pytest.raises(LeanREPLTimeout):
        repl.send("anything")
    assert time.monotonic() - t0 < 5  # did not wait for the 30s sleep
    assert repl._proc is None  # killed, env forfeit


def test_send_before_start_raises():
    with pytest.raises(LeanREPLError):
        LeanREPL(repl_cmd=[sys.executable, "-c", FAKE_REPL]).send("x")


def test_goalstate_is_importable_and_shaped():
    gs = GoalState(goals=[], errors=[])
    assert gs.ok and gs.infos == [] and gs.raw == {}
