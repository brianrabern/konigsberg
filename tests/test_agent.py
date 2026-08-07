"""Agent loop mechanics, driven by a scripted fake model (no provider, no keys).

The load-bearing assertion is test_lying_final_mints_nothing: the model cannot
put a Claim in the ledger by asserting one — only a tool result can.
"""
from __future__ import annotations

from konigsberg_harness.agent import Agent, AgentConfig
from konigsberg_harness.ledger import TrustRoot, mint_conjecture, mint_enumeration
from konigsberg_harness.models import AssistantText, HistoryItem, Tier, ToolCall
from konigsberg_harness.tools.registry import ToolRegistry
from pydantic import BaseModel


class ScriptedModel:
    """Returns queued turns in order; records history it was handed."""

    def __init__(self, responses: list):
        self._responses = list(responses)
        self.histories: list[list[HistoryItem]] = []

    def respond(self, history: list[HistoryItem], tools: list[dict], *, tier: Tier):
        self.histories.append(list(history))
        return self._responses.pop(0)


class _NoteArgs(BaseModel):
    text: str


def _registry_with(**tools) -> ToolRegistry:
    reg = ToolRegistry()
    for name, fn in tools.items():
        # note gets a schema so bad-args validation is testable; others stay free.
        args_model = _NoteArgs if name == "note" else None
        reg.register(name, fn, name, args_model=args_model)
    return reg


# --- loop mechanics -------------------------------------------------------

def test_tool_then_final_records_claim_and_stops():
    reg = _registry_with(note=lambda text: mint_conjecture(text))
    model = ScriptedModel(
        [
            [ToolCall(id="1", name="note", args={"text": "a hunch"})],
            AssistantText("done"),
        ]
    )
    result = Agent(reg, model).run("do a thing")
    assert result.commentary == "done"
    assert "Established (ledger):" in (result.final or "")
    assert "a hunch" in (result.final or "")
    assert "Commentary:" in (result.final or "")
    assert result.steps == 2
    assert len(result.ledger.claims()) == 1
    assert result.ledger.claims()[0].statement == "a hunch"


def test_lying_final_mints_nothing():
    reg = _registry_with(note=lambda text: mint_conjecture(text))
    model = ScriptedModel([AssistantText("I have PROVED the Riemann hypothesis")])
    result = Agent(reg, model).run("prove RH")
    assert result.commentary and result.commentary.startswith("I have PROVED")
    assert "I have PROVED" in (result.final or "")
    assert "nothing established" in (result.final or "")
    assert result.ledger.claims() == ()  # asserting a proof mints no Claim


def test_unknown_tool_becomes_error_observation_and_continues():
    reg = _registry_with(note=lambda text: mint_conjecture(text))
    model = ScriptedModel(
        [
            [ToolCall(id="1", name="does_not_exist", args={})],
            AssistantText("gave up"),
        ]
    )
    result = Agent(reg, model).run("t")
    assert result.commentary == "gave up"
    assert "nothing established" in (result.final or "")
    assert result.ledger.claims() == ()
    assert any(o.is_error for o in result.transcript)


def test_tool_raising_is_captured_not_crashing():
    def boom():
        raise RuntimeError("kaboom")

    reg = _registry_with(boom=boom)
    model = ScriptedModel(
        [
            [ToolCall(id="1", name="boom", args={})],
            AssistantText("ok"),
        ]
    )
    result = Agent(reg, model).run("t")
    assert result.commentary == "ok"
    assert "Commentary:" in (result.final or "")
    assert any(o.is_error and "kaboom" in o.result for o in result.transcript)


def test_bad_args_become_error_tool_result_and_loop_continues():
    """Replaces the old malformed-JSON recovery: ValidationError → error tool_result."""
    reg = _registry_with(note=lambda text: mint_conjecture(text))
    model = ScriptedModel(
        [
            [ToolCall(id="1", name="note", args={"wrong_field": 1})],
            AssistantText("recovered"),
        ]
    )
    result = Agent(reg, model).run("t")
    assert result.commentary == "recovered"
    assert result.ledger.claims() == ()
    assert result.transcript[0].is_error
    assert "ValidationError" in result.transcript[0].result


def test_non_claim_result_is_observed_without_ledgering():
    reg = _registry_with(search=lambda: ["exact foo", "exact bar"])
    model = ScriptedModel(
        [
            [ToolCall(id="1", name="search", args={})],
            AssistantText("done"),
        ]
    )
    result = Agent(reg, model).run("t")
    assert result.ledger.claims() == ()
    assert "exact foo" in result.transcript[0].result


def test_max_steps_reached_without_final():
    # model never finalizes; loop stops at the cap with final=None
    reg = _registry_with(
        note=lambda text: mint_enumeration(text, bound="n<=1", exhaustive=True, tool="note")
    )
    model = ScriptedModel(
        [[ToolCall(id=str(i), name="note", args={"text": "x"})] for i in range(3)]
    )
    result = Agent(reg, model, AgentConfig(max_steps=3)).run("t")
    assert result.final is None
    assert result.steps == 3
    assert len(result.ledger.claims()) == 3


def test_claim_trust_root_is_stamped_by_tool_not_model():
    reg = _registry_with(
        note=lambda text: mint_enumeration(text, bound="n<=5", exhaustive=True, tool="note")
    )
    model = ScriptedModel(
        [
            [ToolCall(id="1", name="note", args={"text": "checked"})],
            AssistantText("x"),
        ]
    )
    result = Agent(reg, model).run("t")
    assert result.ledger.claims()[0].provenance.trust_root is TrustRoot.ENUMERATION


def test_multi_tool_call_turn_answers_every_call():
    reg = _registry_with(note=lambda text: mint_conjecture(text))
    model = ScriptedModel(
        [
            [
                ToolCall(id="a", name="note", args={"text": "one"}),
                ToolCall(id="b", name="note", args={"text": "two"}),
            ],
            AssistantText("done"),
        ]
    )
    result = Agent(reg, model).run("t")
    assert len(result.ledger.claims()) == 2
    # Both tool results must be in history before the final respond.
    last_hist = model.histories[-1]
    ids = [m.id for m in last_hist if hasattr(m, "id") and hasattr(m, "content")]
    assert "a" in ids and "b" in ids
