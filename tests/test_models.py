"""Offline tests for AnthropicModel (no network). Optional live smoke with a key."""
from __future__ import annotations

import os
import sys
from types import ModuleType, SimpleNamespace

import pytest
from konigsberg_harness.models import (
    AnthropicModel,
    AssistantText,
    Tier,
    ToolCall,
    ToolResultMsg,
    UserMsg,
    _history_to_anthropic_messages,
)


def _install_fake_anthropic(monkeypatch, fake_client):
    """Put a minimal `anthropic` module on sys.modules for AnthropicModel."""
    mod = ModuleType("anthropic")

    class Anthropic:
        def __init__(self, api_key: str):
            self.api_key = api_key
            self.messages = fake_client.messages
            fake_client.api_key = api_key
            fake_client.created.append(self)

    mod.Anthropic = Anthropic
    monkeypatch.setitem(sys.modules, "anthropic", mod)
    return mod


class _FakeMessages:
    def __init__(self, response=None):
        self.calls: list = []
        self._response = response

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._response is not None:
            return self._response
        return SimpleNamespace(
            stop_reason="end_turn",
            content=[SimpleNamespace(type="text", text="hello from fake")],
        )


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        AnthropicModel()


def test_missing_sdk_raises(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "anthropic", None)
    with pytest.raises(RuntimeError, match="anthropic package"):
        AnthropicModel()


def test_respond_one_tool_use(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    resp = SimpleNamespace(
        stop_reason="tool_use",
        content=[
            SimpleNamespace(
                type="tool_use",
                id="call_1",
                name="verify_coloring",
                input={"graph6": "Bg", "coloring": [0, 1, 0]},
            )
        ],
    )
    messages = _FakeMessages(resp)
    fake = SimpleNamespace(messages=messages, created=[], api_key=None)
    _install_fake_anthropic(monkeypatch, fake)

    m = AnthropicModel(cheap_model_id="cheap-id", frontier_model_id="frontier-id")
    tools = [
        {
            "name": "verify_coloring",
            "description": "check a coloring",
            "input_schema": {"type": "object", "properties": {}},
        }
    ]
    turn = m.respond([UserMsg("verify P3")], tools, tier=Tier.FRONTIER)
    assert isinstance(turn, list) and len(turn) == 1
    assert turn[0] == ToolCall(
        id="call_1",
        name="verify_coloring",
        args={"graph6": "Bg", "coloring": [0, 1, 0]},
    )
    assert messages.calls[-1]["model"] == "frontier-id"
    assert messages.calls[-1]["tools"] == tools


def test_respond_multiple_tool_use(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    resp = SimpleNamespace(
        stop_reason="tool_use",
        content=[
            SimpleNamespace(type="tool_use", id="a", name="t1", input={"x": 1}),
            SimpleNamespace(type="text", text="ignore me"),
            SimpleNamespace(type="tool_use", id="b", name="t2", input={"y": 2}),
        ],
    )
    messages = _FakeMessages(resp)
    fake = SimpleNamespace(messages=messages, created=[], api_key=None)
    _install_fake_anthropic(monkeypatch, fake)

    m = AnthropicModel()
    turn = m.respond([UserMsg("go")], tools=[], tier=Tier.CHEAP)
    assert turn == [
        ToolCall(id="a", name="t1", args={"x": 1}),
        ToolCall(id="b", name="t2", args={"y": 2}),
    ]
    assert messages.calls[-1]["model"] == m.cheap_model_id


def test_respond_text_only_stop(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    resp = SimpleNamespace(
        stop_reason="end_turn",
        content=[
            SimpleNamespace(type="text", text="all done"),
            SimpleNamespace(type="text", text="!"),
        ],
    )
    messages = _FakeMessages(resp)
    fake = SimpleNamespace(messages=messages, created=[], api_key=None)
    _install_fake_anthropic(monkeypatch, fake)

    m = AnthropicModel()
    turn = m.respond([UserMsg("hi")], tools=[], tier=Tier.CHEAP)
    assert turn == AssistantText("all done!")


def test_join_text_parts_inserts_space_at_word_boundaries():
    from konigsberg_harness.models import _join_text_parts

    assert _join_text_parts(["not", "2-choosable"]) == "not 2-choosable"
    assert _join_text_parts(["on all", "five"]) == "on all five"
    assert _join_text_parts(["using", "reflexivity"]) == "using reflexivity"
    assert _join_text_parts(["all done", "!"]) == "all done!"
    assert _join_text_parts(["hello ", "world"]) == "hello world"


def test_history_translation_groups_tool_blocks():
    history = [
        UserMsg("task"),
        ToolCall(id="1", name="t", args={"a": 1}),
        ToolCall(id="2", name="u", args={}),
        ToolResultMsg(id="1", content="ok"),
        ToolResultMsg(id="2", content="err", is_error=True),
        AssistantText("done"),
    ]
    msgs = _history_to_anthropic_messages(history)
    assert msgs[0] == {"role": "user", "content": "task"}
    assert msgs[1]["role"] == "assistant"
    assert len(msgs[1]["content"]) == 2
    assert msgs[1]["content"][0]["type"] == "tool_use"
    assert msgs[2]["role"] == "user"
    assert msgs[2]["content"][1]["is_error"] is True
    assert msgs[3] == {"role": "assistant", "content": "done"}


def test_env_overrides_default_model_ids(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("ANTHROPIC_CHEAP_MODEL", "env-cheap")
    monkeypatch.setenv("ANTHROPIC_FRONTIER_MODEL", "env-frontier")
    messages = _FakeMessages()
    fake = SimpleNamespace(messages=messages, created=[], api_key=None)
    _install_fake_anthropic(monkeypatch, fake)

    m = AnthropicModel()
    assert m.cheap_model_id == "env-cheap"
    assert m.frontier_model_id == "env-frontier"
    assert m.model_id_for(Tier.CHEAP) == "env-cheap"
    assert m.model_id_for(Tier.FRONTIER) == "env-frontier"


@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="no ANTHROPIC_API_KEY")
def test_live_cheap_smoke():
    """One real cheap call when a key is present (manual / local only)."""
    pytest.importorskip("anthropic")
    m = AnthropicModel()
    text = m.complete("Reply with exactly: pong", tier=Tier.CHEAP)
    assert isinstance(text, str) and text.strip()
