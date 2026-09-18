"""Offline tests for OpenAI-compatible / llama.cpp local models (no network)."""
from __future__ import annotations

import json
import os

import pytest
from konigsberg_harness.models import (
    AssistantText,
    OpenAICompatibleModel,
    Tier,
    ToolCall,
    ToolResultMsg,
    UserMsg,
    _history_to_openai_messages,
    _parse_openai_response,
    _parse_qwen_tool_calls,
    _tools_to_openai,
    build_live_model,
    live_provider,
    normalize_openai_base_url,
)
from konigsberg_harness.repl import Repl, ScriptedReplModel, build_model
from konigsberg_harness.session import SessionStore


def _clear_provider_env(monkeypatch) -> None:
    for key in (
        "KONIGSBERG_PROVIDER",
        "ANTHROPIC_API_KEY",
        "OPENAI_BASE_URL",
        "KONIGSBERG_LLM_BASE_URL",
        "LLAMA_CPP_BASE_URL",
        "KONIGSBERG_MODEL",
        "OPENAI_MODEL",
        "LLAMA_CPP_MODEL",
        "KONIGSBERG_CHEAP_MODEL",
        "OPENAI_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)


class _FakeHTTP:
    """urlopen stand-in: records the Request and returns a JSON body."""

    def __init__(self, payload: dict):
        self.payload = payload
        self.calls: list = []

    def __call__(self, req, timeout=None):
        self.calls.append((req, timeout))
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def test_normalize_openai_base_url():
    assert (
        normalize_openai_base_url("http://127.0.0.1:8080")
        == "http://127.0.0.1:8080/v1"
    )
    assert (
        normalize_openai_base_url("http://127.0.0.1:8080/v1/")
        == "http://127.0.0.1:8080/v1"
    )


def test_live_provider_prefers_anthropic_key(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:8080/v1")
    assert live_provider() == "anthropic"


def test_live_provider_local_override(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("KONIGSBERG_PROVIDER", "local")
    assert live_provider() == "openai"


def test_live_provider_base_url_without_key(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:8080/v1")
    assert live_provider() == "openai"


def test_live_provider_none(monkeypatch):
    _clear_provider_env(monkeypatch)
    assert live_provider() is None


def test_tools_and_history_openai_shape():
    tools = [
        {
            "name": "verify_coloring",
            "description": "check a coloring",
            "input_schema": {"type": "object", "properties": {}},
        }
    ]
    converted = _tools_to_openai(tools)
    assert converted[0]["type"] == "function"
    assert converted[0]["function"]["name"] == "verify_coloring"
    assert converted[0]["function"]["parameters"] == tools[0]["input_schema"]

    history = [
        UserMsg("task"),
        ToolCall(id="1", name="t", args={"a": 1}),
        ToolCall(id="2", name="u", args={}),
        ToolResultMsg(id="1", content="ok"),
        ToolResultMsg(id="2", content="err", is_error=True),
        AssistantText("done"),
    ]
    msgs = _history_to_openai_messages(history, system_prompt="sys")
    assert msgs[0] == {"role": "system", "content": "sys"}
    assert msgs[1] == {"role": "user", "content": "task"}
    assert msgs[2]["role"] == "assistant"
    assert len(msgs[2]["tool_calls"]) == 2
    assert json.loads(msgs[2]["tool_calls"][0]["function"]["arguments"]) == {"a": 1}
    assert msgs[3]["role"] == "tool" and msgs[3]["tool_call_id"] == "1"
    assert msgs[4]["role"] == "tool" and msgs[4]["content"].startswith("[error]")
    assert msgs[5] == {"role": "assistant", "content": "done"}


def test_parse_openai_native_tool_calls():
    turn = _parse_openai_response(
        {
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "verify_coloring",
                                    "arguments": '{"graph6": "Bg"}',
                                },
                            }
                        ],
                    },
                }
            ]
        }
    )
    assert turn == [
        ToolCall(id="call_1", name="verify_coloring", args={"graph6": "Bg"})
    ]


def test_parse_qwen_tool_call_fallback():
    text = (
        "<think>ignore</think>\n"
        '<tool_call>\n{"name": "alon_tarsi", "arguments": {"graph6": "Bg"}}\n'
        "</tool_call>"
    )
    calls = _parse_qwen_tool_calls(text)
    assert calls == [
        ToolCall(id="call_qwen_1", name="alon_tarsi", args={"graph6": "Bg"})
    ]
    turn = _parse_openai_response(
        {"choices": [{"message": {"content": text, "tool_calls": []}}]}
    )
    assert turn == calls


def test_respond_posts_chat_completions(monkeypatch):
    fake = _FakeHTTP(
        {
            "choices": [
                {
                    "message": {
                        "content": "hello from llama",
                        "tool_calls": [],
                    }
                }
            ]
        }
    )
    monkeypatch.setattr("konigsberg_harness.models.urlopen", fake)
    m = OpenAICompatibleModel(
        cheap_model_id="qwen-cheap",
        frontier_model_id="qwen-coder-32b",
        base_url="http://127.0.0.1:8080",
        api_key="local",
        timeout_s=12,
    )
    tools = [
        {
            "name": "verify_coloring",
            "description": "check",
            "input_schema": {"type": "object", "properties": {}},
        }
    ]
    turn = m.respond([UserMsg("hi")], tools, tier=Tier.FRONTIER)
    assert turn == AssistantText("hello from llama")
    assert len(fake.calls) == 1
    req, timeout = fake.calls[0]
    assert timeout == 12
    assert req.full_url == "http://127.0.0.1:8080/v1/chat/completions"
    payload = json.loads(req.data.decode())
    assert payload["model"] == "qwen-coder-32b"
    assert payload["tools"][0]["function"]["name"] == "verify_coloring"
    assert payload["messages"][0]["role"] == "system"


def test_build_live_model_local(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("KONIGSBERG_PROVIDER", "local")
    monkeypatch.setenv("KONIGSBERG_MODEL", "Qwen2.5-Coder-32B-Instruct")
    model = build_live_model()
    assert isinstance(model, OpenAICompatibleModel)
    assert model.frontier_model_id == "Qwen2.5-Coder-32B-Instruct"
    assert model.base_url.endswith("/v1")


def test_build_model_falls_back_scripted(monkeypatch):
    _clear_provider_env(monkeypatch)
    model = build_model()
    assert isinstance(model, ScriptedReplModel)


def test_repl_model_cmd_local(monkeypatch, tmp_path, capsys):
    _clear_provider_env(monkeypatch)
    m = OpenAICompatibleModel(
        frontier_model_id="qwen-coder-32b",
        cheap_model_id="qwen-coder-32b",
        base_url="http://127.0.0.1:8080/v1",
    )
    repl = Repl(store=SessionStore(tmp_path), model=m)
    assert repl.handle_slash("/model") is False
    out = capsys.readouterr().out
    assert "qwen-coder-32b" in out
    assert repl.handle_slash("/model Qwen3-Coder-30B") is False
    assert m.frontier_model_id == "Qwen3-Coder-30B"


@pytest.mark.skipif(
    not (
        os.getenv("OPENAI_BASE_URL")
        or os.getenv("LLAMA_CPP_BASE_URL")
        or os.getenv("KONIGSBERG_PROVIDER", "").lower() in {"local", "openai"}
    ),
    reason="no local LLM endpoint",
)
def test_live_local_smoke():
    """One real local call when llama-server (or similar) is up."""
    m = OpenAICompatibleModel()
    text = m.complete("Reply with exactly: pong", tier=Tier.CHEAP)
    assert isinstance(text, str) and text.strip()
