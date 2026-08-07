"""Agent.step events, interrupt consistency, compaction ledger invariant."""
from __future__ import annotations

from konigsberg_harness.agent import (
    Agent,
    AssistantFinal,
    Interrupted,
    ToolCallProposed,
    ToolResult,
)
from konigsberg_harness.compaction import CompactionConfig, compact, estimate_tokens
from konigsberg_harness.ledger import mint_conjecture
from konigsberg_harness.models import AssistantText, HistoryItem, Tier, ToolCall, UserMsg
from konigsberg_harness.session import Session, SessionStore
from konigsberg_harness.tools.registry import ToolRegistry
from pydantic import BaseModel


class ScriptedModel:
    def __init__(self, responses: list):
        self._responses = list(responses)
        self.histories: list[list[HistoryItem]] = []

    def respond(self, history: list[HistoryItem], tools: list[dict], *, tier: Tier):
        self.histories.append(list(history))
        if not self._responses:
            return AssistantText("(empty)")
        return self._responses.pop(0)


class _NoteArgs(BaseModel):
    text: str


def _reg():
    reg = ToolRegistry()
    reg.register("note", lambda text: mint_conjecture(text), "note", args_model=_NoteArgs)
    return reg


def test_step_event_sequence_tool_then_final():
    model = ScriptedModel(
        [
            [ToolCall(id="1", name="note", args={"text": "hunch"})],
            AssistantText("done"),
        ]
    )
    agent = Agent(_reg(), model)
    session = Session.create()
    session.history.append(UserMsg("go"))
    events = list(agent.step(session))
    types = [type(e).__name__ for e in events]
    assert types == [
        "ModelThinking",
        "ToolCallProposed",
        "ToolResult",
        "ClaimMinted",
        "ModelThinking",
        "AssistantFinal",
    ]
    assert isinstance(events[-1], AssistantFinal)
    assert events[-1].commentary == "done"
    assert "hunch" in events[-1].text
    assert "Established (ledger):" in events[-1].text
    assert len(session.ledger.claims()) == 1


def test_interrupt_after_tool_leaves_consistent_resumable_session(tmp_path):
    """Interrupt mid-turn: every tool_use gets a tool_result; store is loadable."""
    store = SessionStore(tmp_path)
    model = ScriptedModel(
        [
            [
                ToolCall(id="a", name="note", args={"text": "one"}),
                ToolCall(id="b", name="note", args={"text": "two"}),
            ],
            AssistantText("should not reach"),
        ]
    )
    agent = Agent(_reg(), model)
    session = store.create()
    store.log_user(session, "go")

    events = []
    for event in agent.step(session, store=store):
        events.append(event)
        if isinstance(event, ToolCallProposed) and event.call.id == "a":
            agent.request_interrupt()

    assert any(isinstance(e, Interrupted) for e in events)
    # Both calls answered (possibly with ERROR Interrupted for the rest).
    result_ids = {
        e.call.id
        for e in events
        if isinstance(e, ToolResult)
    }
    assert result_ids >= {"a", "b"}

    loaded = store.load(session.id)
    from konigsberg_harness.models import ToolCall as TC
    from konigsberg_harness.models import ToolResultMsg as TR

    open_ids: set[str] = set()
    for item in loaded.history:
        if isinstance(item, TC):
            open_ids.add(item.id)
        elif isinstance(item, TR):
            open_ids.discard(item.id)
    assert not open_ids, f"unanswered tool_use ids: {open_ids}"


def test_compaction_leaves_ledger_identical():
    model = ScriptedModel(
        [AssistantText("Earlier we checked small graphs and found nothing.")]
    )
    session = Session.create()
    # Pad history so there is something to compact away.
    for i in range(20):
        session.history.append(UserMsg(f"message {i} " + ("x" * 50)))
    claim = mint_conjecture("a lasting claim")
    session.ledger.record(claim)
    before = session.ledger.claims()
    before_render = session.ledger.render()

    cfg = CompactionConfig(threshold=10, keep_recent=3)
    assert estimate_tokens(session.history) >= cfg.threshold
    compact(session, model, config=cfg)

    assert session.ledger.claims() == before
    assert session.ledger.render() == before_render
    assert any(isinstance(i, UserMsg) and "Summary" in i.text for i in session.history)
    assert len(session.history) <= cfg.keep_recent + 1


def test_lying_final_at_session_level_mints_nothing(tmp_path):
    store = SessionStore(tmp_path)
    model = ScriptedModel([AssistantText("I have PROVED the Riemann hypothesis")])
    agent = Agent(_reg(), model)
    session = store.create()
    result = agent.run("prove RH", session=session, store=store)
    assert result.commentary and result.commentary.startswith("I have PROVED")
    assert "nothing established" in (result.final or "")
    assert result.ledger.claims() == ()
    loaded = store.load(session.id)
    assert loaded.ledger.claims() == ()
