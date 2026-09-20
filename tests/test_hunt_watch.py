"""hunt_watch: expected tool rejections are not hunt-health errors."""
from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hunt_watch.py"
_SPEC = importlib.util.spec_from_file_location("hunt_watch", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
hunt_watch = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(hunt_watch)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ago(seconds: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat()


def _tr(content: str, *, err: bool = True, at: str | None = None) -> dict:
    return {
        "type": "tool_result",
        "is_error": err,
        "content": content,
        "at": at or _now(),
    }


def test_expected_discharging_and_ctrl_c_are_not_health_errors():
    events = [
        {"type": "session_meta", "id": "abc", "created_at": _now()},
        _tr("ERROR ValueError: μ must specify degrees 8 and 9"),
        _tr("ERROR ValueError: non-conserving rule: to_pattern '9' is not a neighbor transfer"),
        _tr("ERROR error: Caught keyboard interrupt"),
        _tr("ERROR AttributeError: module 'networkx' has no attribute 'join'"),
        _tr("ERROR ValueError: unknown graph kind 'join'; want one of ['complete',"),
        _tr("ERROR ValueError: kind='join' is Zykov G ∨ H; pass graph6= and other="),
        _tr("ERROR ValueError: LEAN COMPILE MISS (not a kernel proof) `foo`: type mismatch."),
        _tr("ERROR ValueError: statement does not elaborate: ['type expected, got\\n  (Konigsberg.Literature.Coloring.CranstonRabern_BKEquivalentConjectures.equivalent_K3_join_E6 : …)']"),
        _tr("ERROR ValidationError: 4 validation errors for DischargingArgs\nD\n  Field required"),
        _tr("ERROR LeanREPLError: #print axioms k3_join_E6_fChoosable_degreeSpec failed"),
        _tr("ERROR ValueError: proof failed: [\"invalid 'import' command, it must be used"),
        _tr("ERROR ToolBudgetExceeded: TOOL BUDGET EXCEEDED: choosability_refute — n=9 exceeds live cap 6"),
        _tr("ERROR ValueError: from_edges requires n= and edges="),
        _tr("ERROR ValueError: bad edge (4,6) for n=6"),
        _tr("ERROR ValueError: ledger coupling: forbidden cores not minted reducible: Bw"),
        _tr("ERROR LeanREPLError: REPL is not running; call start() (or restart()) first"),
        _tr("ERROR LeanREPLTimeout: no complete reply within 180s; process killed"),
        _tr("ERROR LeanREPLError: retract: no session declaration matching 'K3J6'"),
    ]
    s = hunt_watch.summarize(events)
    assert s["n_err"] == 0
    assert s["n_err_recent"] == 0
    assert s["last_err"] == ""


def test_unexpected_timeout_still_flags_health():
    events = [
        {"type": "session_meta", "id": "abc", "created_at": _now()},
        _tr("ERROR TimeoutError: The read operation timed out"),
    ]
    s = hunt_watch.summarize(events)
    assert s["n_err"] == 1
    assert s["n_err_recent"] == 1
    assert "timed out" in s["last_err"]


def test_lean_unavoidable_name_is_not_discharging_closed():
    """Lemma names containing 'unavoidable' are lean-proofs, not μ closures."""
    events = [
        {"type": "session_meta", "id": "abc", "created_at": _now()},
        {
            "type": "claim",
            "statement": (
                "BK.DischargingClosure."
                "reducible_and_unavoidable_imp_no_counterexample_durable"
            ),
            "provenance": {"tool": "lean_prove", "durable": True},
            "at": _now(),
        },
        {"type": "lemma", "lean_name": (
            "BK.DischargingClosure."
            "reducible_and_unavoidable_imp_no_counterexample_durable"
        ), "durable": True, "at": _now()},
        {"type": "tool_call", "id": "1", "name": "discharging_unavoidable",
         "at": _now()},
        {"type": "tool_result", "id": "1", "is_error": False,
         "content": "inconclusive: argument does not close", "at": _now()},
    ]
    s = hunt_watch.summarize(events)
    assert s["kinds"]["lean-proof"] == 1
    assert s["kinds"].get("discharging", 0) == 0
    assert s["disc_closed"] == 0
    assert s["disc_attempts"] == 1
    flashes = hunt_watch._flashes({"cores": [], "durable": [], "disc_closed": 0,
                                   "last_discharge": None, "settlement": None}, s)
    assert not any("DISCHARGING CLOSED" in f for f in flashes)


def test_discharging_hit_still_counts_as_closed():
    stmt = (
        "UNAVOIDABLE (BK D=9 discharging): cores=EFzw "
        "in every 9-critical K_9-free graph."
    )
    events = [
        {"type": "session_meta", "id": "abc", "created_at": _now()},
        {
            "type": "claim",
            "statement": stmt,
            "provenance": {"tool": "discharging_unavoidable", "durable": False},
            "at": _now(),
        },
        {"type": "tool_call", "id": "1", "name": "discharging_unavoidable",
         "at": _now()},
    ]
    s = hunt_watch.summarize(events)
    assert s["kinds"]["discharging"] == 1
    assert s["disc_closed"] == 1
    flashes = hunt_watch._flashes({"cores": [], "durable": [], "disc_closed": 0,
                                   "last_discharge": None, "settlement": None}, s)
    assert any("DISCHARGING CLOSED" in f for f in flashes)


def test_frontier_claim_is_not_discharging_closed():
    stmt = (
        "DISCHARGING_SEARCH STUCK survivors=9 deficit=9 C=0 iters=4 "
        "residual=deg9(high=0,low=9). IRREDUCIBLE-FRONTIER "
        "(BK D=9 discharging): residual types=deg9(high=0,low=9) "
        "(proves nothing; not a forbidden configuration)."
    )
    events = [
        {"type": "session_meta", "id": "abc", "created_at": _now()},
        {
            "type": "claim",
            "statement": stmt,
            "provenance": {"tool": "discharging_search", "durable": False},
            "at": _now(),
        },
        {"type": "tool_call", "id": "1", "name": "discharging_search",
         "at": _now()},
        {"type": "tool_result", "id": "1", "is_error": False,
         "content": stmt, "at": _now()},
    ]
    s = hunt_watch.summarize(events)
    assert s["kinds"].get("discharging", 0) == 0
    assert s["kinds"]["irreducible-frontier"] == 1
    assert s["disc_closed"] == 0
    assert s["disc_attempts"] == 1
    assert s["last_search"] is not None
    assert "STUCK" in s["last_search"]
    flashes = hunt_watch._flashes({"cores": [], "durable": [], "disc_closed": 0,
                                   "last_discharge": None, "settlement": None}, s)
    assert not any("DISCHARGING CLOSED" in f for f in flashes)


def test_compile_miss_is_dim_feed_not_red_error():
    miss = _tr("ERROR ValueError: LEAN COMPILE MISS (not a kernel proof) `foo`: type mismatch.")
    boom = _tr("ERROR TimeoutError: The read operation timed out")
    miss_line = hunt_watch._feed_line("tool_result", None, miss)
    boom_line = hunt_watch._feed_line("tool_result", None, boom)
    assert "⟵ miss" in miss_line
    assert "✗ error" not in miss_line
    assert "✗ error" in boom_line


def test_stale_unexpected_error_does_not_paint_recent():
    events = [
        {"type": "session_meta", "id": "abc", "created_at": _ago(3600)},
        _tr("ERROR TimeoutError: The read operation timed out", at=_ago(3600)),
        {"type": "user", "text": "STAIRCASE", "at": _now()},
    ]
    s = hunt_watch.summarize(events)
    assert s["n_err"] == 1
    assert s["n_err_recent"] == 0
    panel = hunt_watch.render(s, [])
    assert "⚠ tool errors" not in panel
    assert "stale tool errors 1" in panel
