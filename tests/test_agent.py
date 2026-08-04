"""Agent loop mechanics, driven by a scripted fake model (no provider, no keys).

The load-bearing assertion is test_lying_final_mints_nothing: the model cannot
put a Claim in the ledger by asserting one — only a tool result can.
"""
import pytest
from konigsberg_harness.agent import Agent, AgentConfig, _parse_action
from konigsberg_harness.ledger import TrustRoot, mint_conjecture, mint_enumeration
from konigsberg_harness.models import Tier
from konigsberg_harness.tools.registry import ToolRegistry


class ScriptedModel:
    """Returns queued responses in order; records prompts it was given."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.prompts: list[str] = []

    def complete(self, prompt, *, tier: Tier) -> str:
        self.prompts.append(prompt)
        return self._responses.pop(0)


def _registry_with(**tools) -> ToolRegistry:
    reg = ToolRegistry()
    for name, fn in tools.items():
        reg.register(name, fn, name)
    return reg


# --- _parse_action --------------------------------------------------------

def test_parse_action_plain_json():
    assert _parse_action('{"final": "ok"}') == {"final": "ok"}


def test_parse_action_strips_code_fences():
    assert _parse_action('```json\n{"tool": "t", "args": {}}\n```') == {"tool": "t", "args": {}}


def test_parse_action_rejects_non_object():
    with pytest.raises(ValueError):
        _parse_action("[1, 2, 3]")


def test_parse_action_rejects_garbage():
    with pytest.raises(ValueError):
        _parse_action("not json at all")


# --- loop mechanics -------------------------------------------------------

def test_tool_then_final_records_claim_and_stops():
    reg = _registry_with(note=lambda text: mint_conjecture(text))
    model = ScriptedModel(
        [
            '{"tool": "note", "args": {"text": "a hunch"}}',
            '{"final": "done"}',
        ]
    )
    result = Agent(reg, model).run("do a thing")
    assert result.final == "done"
    assert result.steps == 2
    assert len(result.ledger.claims()) == 1
    assert result.ledger.claims()[0].statement == "a hunch"


def test_lying_final_mints_nothing():
    reg = _registry_with(note=lambda text: mint_conjecture(text))
    model = ScriptedModel(['{"final": "I have PROVED the Riemann hypothesis"}'])
    result = Agent(reg, model).run("prove RH")
    assert result.final.startswith("I have PROVED")
    assert result.ledger.claims() == ()  # asserting a proof mints no Claim


def test_unknown_tool_becomes_error_observation_and_continues():
    reg = _registry_with(note=lambda text: mint_conjecture(text))
    model = ScriptedModel(
        ['{"tool": "does_not_exist", "args": {}}', '{"final": "gave up"}']
    )
    result = Agent(reg, model).run("t")
    assert result.final == "gave up"
    assert result.ledger.claims() == ()
    assert any(o.is_error for o in result.transcript)


def test_tool_raising_is_captured_not_crashing():
    def boom():
        raise RuntimeError("kaboom")

    reg = _registry_with(boom=boom)
    model = ScriptedModel(['{"tool": "boom", "args": {}}', '{"final": "ok"}'])
    result = Agent(reg, model).run("t")
    assert result.final == "ok"
    assert any(o.is_error and "kaboom" in o.result for o in result.transcript)


def test_unparseable_action_is_captured_and_loop_continues():
    reg = _registry_with(note=lambda text: mint_conjecture(text))
    model = ScriptedModel(["garbage {{{", '{"final": "recovered"}'])
    result = Agent(reg, model).run("t")
    assert result.final == "recovered"
    assert result.transcript[0].is_error


def test_non_claim_result_is_observed_without_ledgering():
    reg = _registry_with(search=lambda: ["exact foo", "exact bar"])
    model = ScriptedModel(['{"tool": "search", "args": {}}', '{"final": "done"}'])
    result = Agent(reg, model).run("t")
    assert result.ledger.claims() == ()
    assert "exact foo" in result.transcript[0].result


def test_max_steps_reached_without_final():
    # model never finalizes; loop stops at the cap with final=None
    reg = _registry_with(
        note=lambda text: mint_enumeration(text, bound="n<=1", exhaustive=True, tool="note")
    )
    model = ScriptedModel(['{"tool": "note", "args": {"text": "x"}}'] * 3)
    result = Agent(reg, model, AgentConfig(max_steps=3)).run("t")
    assert result.final is None
    assert result.steps == 3
    assert len(result.ledger.claims()) == 3


def test_claim_trust_root_is_stamped_by_tool_not_model():
    reg = _registry_with(
        note=lambda text: mint_enumeration(text, bound="n<=5", exhaustive=True, tool="note")
    )
    model = ScriptedModel(['{"tool": "note", "args": {"text": "checked"}}', '{"final": "x"}'])
    result = Agent(reg, model).run("t")
    assert result.ledger.claims()[0].provenance.trust_root is TrustRoot.ENUMERATION
