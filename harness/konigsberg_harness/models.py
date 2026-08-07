"""Provider routing (open decision #5) + normalized tool-use turn types.

Policy: cheap models dispatch empirical tools and triage; a frontier model drives
proof search. Tier is chosen per call by the loop/caller — no routing DSL.

The loop talks to models via `respond` (conversation + tool schemas → structured
turn). Provider-specific block shapes stay inside `AnthropicModel`.

API keys are read from the environment ONLY. Never from a file or constructor arg.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

from .grounding import GROUNDING_SYSTEM_PROMPT

# Defaults are config, not buried in call sites. Override via constructor or env.
_DEFAULT_CHEAP = "claude-haiku-4-5-20251001"
_DEFAULT_FRONTIER = "claude-sonnet-4-5-20250929"
_ENV_CHEAP = "ANTHROPIC_CHEAP_MODEL"
_ENV_FRONTIER = "ANTHROPIC_FRONTIER_MODEL"
_ENV_KEY = "ANTHROPIC_API_KEY"


class Tier(Enum):
    CHEAP = "cheap"  # empirical dispatch, routing, summarization
    FRONTIER = "frontier"  # proof search, hard lemma decomposition


# --- Normalized turn types (provider-agnostic) ----------------------------


@dataclass(frozen=True)
class ToolCall:
    """The model wants to run a tool."""

    id: str  # provider-issued id; echoed back in the result
    name: str
    args: dict


@dataclass(frozen=True)
class ToolResultMsg:
    """Our reply to a ToolCall."""

    id: str
    content: str
    is_error: bool = False


@dataclass(frozen=True)
class UserMsg:
    text: str


@dataclass(frozen=True)
class AssistantText:
    """A plain (final) turn, no tool call."""

    text: str


HistoryItem = UserMsg | ToolCall | ToolResultMsg | AssistantText
Turn = list[ToolCall] | AssistantText


class Model(Protocol):
    """What the agent loop needs from a model. Any provider (or a test fake)
    satisfies this; the loop never depends on a concrete SDK."""

    def respond(
        self,
        history: list[HistoryItem],
        tools: list[dict],
        *,
        tier: Tier,
    ) -> Turn: ...


def _default_cheap_id() -> str:
    return os.environ.get(_ENV_CHEAP, _DEFAULT_CHEAP)


def _default_frontier_id() -> str:
    return os.environ.get(_ENV_FRONTIER, _DEFAULT_FRONTIER)


def _history_to_anthropic_messages(history: list[HistoryItem]) -> list[dict]:
    """Flatten our history into Anthropic messages (group tool_use / tool_result)."""
    messages: list[dict] = []
    i = 0
    n = len(history)
    while i < n:
        item = history[i]
        if isinstance(item, UserMsg):
            messages.append({"role": "user", "content": item.text})
            i += 1
        elif isinstance(item, AssistantText):
            messages.append({"role": "assistant", "content": item.text})
            i += 1
        elif isinstance(item, ToolCall):
            blocks: list[dict] = []
            while i < n and isinstance(history[i], ToolCall):
                tc = history[i]
                assert isinstance(tc, ToolCall)
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.args,
                    }
                )
                i += 1
            messages.append({"role": "assistant", "content": blocks})
        elif isinstance(item, ToolResultMsg):
            blocks = []
            while i < n and isinstance(history[i], ToolResultMsg):
                tr = history[i]
                assert isinstance(tr, ToolResultMsg)
                block: dict = {
                    "type": "tool_result",
                    "tool_use_id": tr.id,
                    "content": tr.content,
                }
                if tr.is_error:
                    block["is_error"] = True
                blocks.append(block)
                i += 1
            messages.append({"role": "user", "content": blocks})
        else:
            raise TypeError(f"unknown history item: {type(item)!r}")
    return messages


def _parse_anthropic_response(msg: object) -> Turn:
    """Map an Anthropic Messages response onto our Turn type."""
    stop = getattr(msg, "stop_reason", None)
    content = getattr(msg, "content", []) or []
    if stop == "tool_use":
        calls: list[ToolCall] = []
        for block in content:
            if getattr(block, "type", None) != "tool_use":
                continue
            calls.append(
                ToolCall(
                    id=str(block.id),
                    name=str(block.name),
                    args=dict(block.input or {}),
                )
            )
        if not calls:
            raise RuntimeError("stop_reason=tool_use but no tool_use blocks in content")
        return calls
    parts: list[str] = []
    for block in content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return AssistantText(_join_text_parts(parts))


def _join_text_parts(parts: list[str]) -> str:
    """Concatenate Anthropic text blocks without dropping spaces at boundaries.

    Blocks are often split on word boundaries with the space omitted from both
    sides; inserting a single space there keeps transcripts readable. Do not
    insert before punctuation (so \"all done\" + \"!\" stays \"all done!\").
    """
    if not parts:
        return ""
    out = parts[0]
    for part in parts[1:]:
        if not part:
            continue
        if not out:
            out = part
            continue
        left, right = out[-1], part[0]
        if (
            not left.isspace()
            and not right.isspace()
            and right not in ".,!?;:)]}…\"'"
            and left not in "([{/\""
        ):
            out += " "
        out += part
    return out


@dataclass
class AnthropicModel:
    """Anthropic Messages API behind the `Model` protocol (native tool use).

    Key: `ANTHROPIC_API_KEY` env only. The `anthropic` package is the optional
    `providers` extra — imported lazily so the rest of the harness stays free of it.
    """

    cheap_model_id: str = field(default_factory=_default_cheap_id)
    frontier_model_id: str = field(default_factory=_default_frontier_id)
    max_tokens: int = 4096
    system_prompt: str = GROUNDING_SYSTEM_PROMPT
    _client: object = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        key = os.environ.get(_ENV_KEY)
        if not key:
            raise RuntimeError(
                f"{_ENV_KEY} is not set. Export it in the environment "
                "(never pass the key as an argument or read it from a file)."
            )
        try:
            import anthropic  # optional providers extra
        except ImportError as e:
            raise RuntimeError(
                "anthropic package not installed; "
                "install the harness providers extra: "
                "`uv sync --extra providers` / `pip install 'konigsberg-harness[providers]'`"
            ) from e
        self._client = anthropic.Anthropic(api_key=key)

    def model_id_for(self, tier: Tier) -> str:
        if tier is Tier.CHEAP:
            return self.cheap_model_id
        if tier is Tier.FRONTIER:
            return self.frontier_model_id
        raise ValueError(f"unknown tier: {tier!r}")

    def respond(
        self,
        history: list[HistoryItem],
        tools: list[dict],
        *,
        tier: Tier,
    ) -> Turn:
        model_id = self.model_id_for(tier)
        kwargs: dict = {
            "model": model_id,
            "max_tokens": self.max_tokens,
            "messages": _history_to_anthropic_messages(history),
            "system": self.system_prompt,
        }
        if tools:
            kwargs["tools"] = tools
        msg = self._client.messages.create(**kwargs)  # type: ignore[union-attr]
        return _parse_anthropic_response(msg)

    def complete(self, prompt: str, *, tier: Tier) -> str:
        """Stateless text-only call (smoke / non-agent callers). Loop uses `respond`."""
        turn = self.respond([UserMsg(prompt)], tools=[], tier=tier)
        if isinstance(turn, AssistantText):
            return turn.text
        raise RuntimeError("complete() expected a text turn, got tool_use")


@dataclass
class ModelRouter:
    """Tier-routing policy wrapper. Delegates to `AnthropicModel` by default."""

    cheap_model: str = field(default_factory=_default_cheap_id)
    frontier_model: str = field(default_factory=_default_frontier_id)
    _provider: AnthropicModel = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._provider = AnthropicModel(
            cheap_model_id=self.cheap_model,
            frontier_model_id=self.frontier_model,
        )

    def respond(
        self,
        history: list[HistoryItem],
        tools: list[dict],
        *,
        tier: Tier,
    ) -> Turn:
        return self._provider.respond(history, tools, tier=tier)

    def complete(self, prompt: str, *, tier: Tier) -> str:
        return self._provider.complete(prompt, tier=tier)
