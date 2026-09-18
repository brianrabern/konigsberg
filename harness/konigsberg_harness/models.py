"""Provider routing (open decision #5) + normalized tool-use turn types.

Policy: cheap models dispatch empirical tools and triage; a frontier model drives
proof search. Tier is chosen per call by the loop/caller — no routing DSL.

The loop talks to models via `respond` (conversation + tool schemas → structured
turn). Provider-specific block shapes stay inside `AnthropicModel` /
`OpenAICompatibleModel` (llama.cpp, vLLM, Ollama, LM Studio, cloud OpenAI).

API keys are read from ``os.environ`` only — never constructor args. The REPL
loads a gitignored repo-root ``.env`` into the environment at startup
(``envfile.load_project_env``); shell exports still win.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .grounding import GROUNDING_SYSTEM_PROMPT
from .model_catalog import resolve_model_id

# Defaults are config, not buried in call sites. Override via constructor, env,
# or REPL `/model`. Short aliases (opus, sonnet, fable, …) resolve via model_catalog.
#
# The chat agent always uses the "frontier" / primary model. The "cheap" id is
# only for background work (e.g. compaction) — not something you pick turn-by-turn.
_DEFAULT_CHEAP = "claude-haiku-4-5"
_DEFAULT_FRONTIER = "claude-opus-4-8"
_ENV_CHEAP = "ANTHROPIC_CHEAP_MODEL"
_ENV_FRONTIER = "ANTHROPIC_FRONTIER_MODEL"
_ENV_MODEL = "ANTHROPIC_MODEL"  # preferred alias for the chat (frontier) model
_ENV_KEY = "ANTHROPIC_API_KEY"

_ENV_PROVIDER = "KONIGSBERG_PROVIDER"
_ENV_OPENAI_BASE = "OPENAI_BASE_URL"
_ENV_LLM_BASE = "KONIGSBERG_LLM_BASE_URL"
_ENV_LLAMA_BASE = "LLAMA_CPP_BASE_URL"
_ENV_OPENAI_KEY = "OPENAI_API_KEY"
_ENV_LLAMA_KEY = "LLAMA_CPP_API_KEY"
_ENV_LOCAL_MODEL = "KONIGSBERG_MODEL"
_ENV_OPENAI_MODEL = "OPENAI_MODEL"
_ENV_LLAMA_MODEL = "LLAMA_CPP_MODEL"
_ENV_LOCAL_CHEAP = "KONIGSBERG_CHEAP_MODEL"
_ENV_TIMEOUT = "KONIGSBERG_LLM_TIMEOUT"
_ENV_MAX_TOKENS = "KONIGSBERG_MAX_TOKENS"
_DEFAULT_LOCAL_BASE = "http://127.0.0.1:8080/v1"
_DEFAULT_LOCAL_MODEL = "local"
_DEFAULT_LOCAL_TIMEOUT = 600.0

_LOCAL_PROVIDER_NAMES = frozenset(
    {"openai", "local", "llama.cpp", "llamacpp", "openai-compat"}
)
_ANTHROPIC_PROVIDER_NAMES = frozenset({"anthropic", "claude"})


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
    return resolve_model_id(os.environ.get(_ENV_CHEAP, _DEFAULT_CHEAP))


def _default_frontier_id() -> str:
    # ANTHROPIC_MODEL is the simple knob; FRONTIER_MODEL kept for compatibility.
    spec = os.environ.get(_ENV_MODEL) or os.environ.get(_ENV_FRONTIER, _DEFAULT_FRONTIER)
    return resolve_model_id(spec)


def live_provider() -> str | None:
    """``'anthropic'`` | ``'openai'`` | ``None`` (scripted / offline).

    Explicit ``KONIGSBERG_PROVIDER`` wins. Otherwise an Anthropic key selects
    Claude (backward compatible — a stray ``OPENAI_BASE_URL`` from another tool
    must not steal the session). A local/llama.cpp URL without a key selects
    the OpenAI-compatible path. ``KONIGSBERG_PROVIDER=local`` forces llama.cpp
    even when ``ANTHROPIC_API_KEY`` is also set.
    """
    explicit = os.environ.get(_ENV_PROVIDER, "").strip().lower()
    if explicit in _ANTHROPIC_PROVIDER_NAMES:
        return "anthropic"
    if explicit in _LOCAL_PROVIDER_NAMES:
        return "openai"
    if os.environ.get(_ENV_KEY):
        return "anthropic"
    if _configured_openai_base_url():
        return "openai"
    return None


def has_live_provider() -> bool:
    return live_provider() is not None


def _configured_openai_base_url() -> str | None:
    for key in (_ENV_OPENAI_BASE, _ENV_LLM_BASE, _ENV_LLAMA_BASE):
        raw = os.environ.get(key, "").strip()
        if raw:
            return raw
    return None


def normalize_openai_base_url(raw: str) -> str:
    """``http://host:8080`` → ``http://host:8080/v1``; leave ``…/v1`` alone."""
    url = raw.strip().rstrip("/")
    if not url:
        raise ValueError("empty OpenAI base URL")
    if url.endswith("/v1"):
        return url
    return f"{url}/v1"


def _default_openai_base_url() -> str:
    raw = _configured_openai_base_url() or _DEFAULT_LOCAL_BASE
    return normalize_openai_base_url(raw)


def _default_openai_frontier_id() -> str:
    return (
        os.environ.get(_ENV_LOCAL_MODEL)
        or os.environ.get(_ENV_OPENAI_MODEL)
        or os.environ.get(_ENV_LLAMA_MODEL)
        or _DEFAULT_LOCAL_MODEL
    )


def _default_openai_cheap_id() -> str:
    return os.environ.get(_ENV_LOCAL_CHEAP) or _default_openai_frontier_id()


def _default_openai_timeout() -> float:
    raw = os.environ.get(_ENV_TIMEOUT, "").strip()
    if raw:
        return float(raw)
    return _DEFAULT_LOCAL_TIMEOUT


def _default_max_tokens() -> int:
    raw = os.environ.get(_ENV_MAX_TOKENS, "").strip()
    if raw:
        return int(raw)
    return 4096


def default_frontier_id() -> str:
    """Frontier model id for the active provider (UI health line)."""
    kind = live_provider()
    if kind == "openai":
        return _default_openai_frontier_id()
    return _default_frontier_id()


def is_live_model(model: object) -> bool:
    """True when ``model`` can switch ids and carry a system prompt (not scripted)."""
    return hasattr(model, "set_model_id") and hasattr(model, "frontier_model_id")


def model_provider_kind(model: object) -> str | None:
    if isinstance(model, OpenAICompatibleModel):
        return "openai"
    if isinstance(model, AnthropicModel):
        return "anthropic"
    return None


def build_live_model(
    *,
    system_prompt: str = GROUNDING_SYSTEM_PROMPT,
    temperature: float | None = None,
) -> AnthropicModel | OpenAICompatibleModel:
    """Construct the configured live provider. Raises if none is configured."""
    kind = live_provider()
    if kind == "openai":
        return OpenAICompatibleModel(
            system_prompt=system_prompt, temperature=temperature
        )
    if kind == "anthropic":
        return AnthropicModel(system_prompt=system_prompt, temperature=temperature)
    raise RuntimeError(
        "no live LLM provider configured. Set OPENAI_BASE_URL (llama.cpp) or "
        "ANTHROPIC_API_KEY, or KONIGSBERG_PROVIDER=local."
    )


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

    Key: `ANTHROPIC_API_KEY` from the environment (REPL may preload ``.env``).
    The `anthropic` package is the optional `providers` extra — imported lazily
    so the rest of the harness stays free of it.
    """

    cheap_model_id: str = field(default_factory=_default_cheap_id)
    frontier_model_id: str = field(default_factory=_default_frontier_id)
    max_tokens: int = 4096
    system_prompt: str = GROUNDING_SYSTEM_PROMPT
    temperature: float | None = None  # None → API default; referee uses higher
    _client: object = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        # Allow constructing with aliases (opus / sonnet / …).
        self.cheap_model_id = resolve_model_id(self.cheap_model_id)
        self.frontier_model_id = resolve_model_id(self.frontier_model_id)
        key = os.environ.get(_ENV_KEY)
        if not key:
            raise RuntimeError(
                f"{_ENV_KEY} is not set. Put it in the repo-root `.env` or export "
                "it in the shell (never pass the key as a constructor argument)."
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

    def set_model_id(self, tier: Tier, spec: str) -> str:
        """Set cheap/frontier from an alias or full id; return the resolved id."""
        mid = resolve_model_id(spec)
        if tier is Tier.CHEAP:
            self.cheap_model_id = mid
        elif tier is Tier.FRONTIER:
            self.frontier_model_id = mid
        else:
            raise ValueError(f"unknown tier: {tier!r}")
        return mid

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
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        if tools:
            kwargs["tools"] = tools
        try:
            msg = self._client.messages.create(**kwargs)  # type: ignore[union-attr]
        except Exception as e:
            # Some frontier models reject temperature — retry without it.
            err = str(e).lower()
            if "temperature" in err and "temperature" in kwargs:
                retry = {k: v for k, v in kwargs.items() if k != "temperature"}
                msg = self._client.messages.create(**retry)  # type: ignore[union-attr]
            else:
                raise
        return _parse_anthropic_response(msg)

    def complete(self, prompt: str, *, tier: Tier) -> str:
        """Stateless text-only call (smoke / non-agent callers). Loop uses `respond`."""
        turn = self.respond([UserMsg(prompt)], tools=[], tier=tier)
        if isinstance(turn, AssistantText):
            return turn.text
        raise RuntimeError("complete() expected a text turn, got tool_use")


def _tools_to_openai(tools: list[dict]) -> list[dict]:
    """Anthropic ``{name, description, input_schema}`` → OpenAI function tools."""
    out: list[dict] = []
    for t in tools:
        out.append(
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description") or "",
                    "parameters": t.get("input_schema")
                    or {"type": "object", "properties": {}},
                },
            }
        )
    return out


def _history_to_openai_messages(
    history: list[HistoryItem], *, system_prompt: str = ""
) -> list[dict]:
    """Flatten our history into OpenAI chat messages (one ``tool`` msg per result)."""
    messages: list[dict] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
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
            tool_calls: list[dict] = []
            while i < n and isinstance(history[i], ToolCall):
                tc = history[i]
                assert isinstance(tc, ToolCall)
                tool_calls.append(
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.args),
                        },
                    }
                )
                i += 1
            messages.append(
                {"role": "assistant", "content": "", "tool_calls": tool_calls}
            )
        elif isinstance(item, ToolResultMsg):
            while i < n and isinstance(history[i], ToolResultMsg):
                tr = history[i]
                assert isinstance(tr, ToolResultMsg)
                content = tr.content
                if tr.is_error:
                    content = f"[error] {content}"
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tr.id,
                        "content": content,
                    }
                )
                i += 1
        else:
            raise TypeError(f"unknown history item: {type(item)!r}")
    return messages


def _json_object(value: object) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _parse_qwen_tool_calls(text: str) -> list[ToolCall]:
    """Qwen / Hermes ``<tool_call>{...}</tool_call>`` dumped into assistant text.

    Only this tagged JSON form — not markdown fences (that failure class is why
    the loop uses native tool use).
    """
    calls: list[ToolCall] = []
    start_tag, end_tag = "<tool_call>", "</tool_call>"
    pos = 0
    n = 0
    while True:
        i = text.find(start_tag, pos)
        if i < 0:
            break
        j = text.find(end_tag, i)
        if j < 0:
            break
        blob = text[i + len(start_tag) : j].strip()
        pos = j + len(end_tag)
        try:
            obj = json.loads(blob)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        fn = obj.get("function")
        if isinstance(fn, dict):
            name = fn.get("name")
            args = _json_object(fn.get("arguments") or fn.get("parameters"))
        else:
            name = obj.get("name")
            args = _json_object(
                obj.get("arguments") or obj.get("parameters") or obj.get("input")
            )
        if not name:
            continue
        n += 1
        calls.append(ToolCall(id=f"call_qwen_{n}", name=str(name), args=args))
    return calls


_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def _parse_openai_response(payload: dict) -> Turn:
    """Map an OpenAI-style chat.completions body onto our Turn type."""
    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError("LLM response had no choices")
    choice = choices[0] if isinstance(choices[0], dict) else {}
    message = choice.get("message") or {}
    if not isinstance(message, dict):
        message = {}
    raw_calls = message.get("tool_calls") or []
    calls: list[ToolCall] = []
    for i, tc in enumerate(raw_calls, start=1):
        if not isinstance(tc, dict):
            continue
        fn = tc.get("function") or {}
        if not isinstance(fn, dict):
            fn = {}
        name = fn.get("name") or tc.get("name")
        if not name:
            continue
        args = _json_object(fn.get("arguments") or tc.get("arguments") or {})
        calls.append(
            ToolCall(id=str(tc.get("id") or f"call_{i}"), name=str(name), args=args)
        )
    if calls:
        return calls
    content = message.get("content") or ""
    if not isinstance(content, str):
        content = str(content)
    stripped = _THINK_RE.sub("", content).strip()
    qwen_calls = _parse_qwen_tool_calls(stripped)
    if qwen_calls:
        return qwen_calls
    return AssistantText(stripped)


def _post_chat_completions(
    url: str,
    payload: dict,
    *,
    api_key: str,
    timeout_s: float,
) -> dict:
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    req = Request(url, data=body, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8")
    except HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8", errors="replace")[:800]
        except Exception:  # noqa: BLE001
            err_body = ""
        raise RuntimeError(f"LLM HTTP {e.code} at {url}: {err_body or e.reason}") from e
    except URLError as e:
        raise RuntimeError(
            f"cannot reach LLM at {url} ({e.reason}). "
            "Is llama-server running? Set OPENAI_BASE_URL / LLAMA_CPP_BASE_URL."
        ) from e
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"LLM returned non-JSON from {url}: {raw[:400]}") from e
    if not isinstance(parsed, dict):
        raise RuntimeError(  # noqa: TRY004
            f"LLM JSON was not an object: {type(parsed).__name__}"
        )
    return parsed


@dataclass
class OpenAICompatibleModel:
    """OpenAI Chat Completions behind the `Model` protocol (llama.cpp, vLLM, …).

    Talks HTTP to ``OPENAI_BASE_URL`` (default ``http://127.0.0.1:8080/v1``).
    No SDK — stdlib only. ``OPENAI_API_KEY`` is optional locally (llama.cpp
    ignores it unless started with ``--api-key``).
    """

    cheap_model_id: str = field(default_factory=_default_openai_cheap_id)
    frontier_model_id: str = field(default_factory=_default_openai_frontier_id)
    base_url: str = field(default_factory=_default_openai_base_url)
    api_key: str = field(
        default_factory=lambda: os.environ.get(_ENV_OPENAI_KEY)
        or os.environ.get(_ENV_LLAMA_KEY)
        or "local"
    )
    max_tokens: int = field(default_factory=_default_max_tokens)
    system_prompt: str = GROUNDING_SYSTEM_PROMPT
    temperature: float | None = None
    timeout_s: float = field(default_factory=_default_openai_timeout)

    def __post_init__(self) -> None:
        self.cheap_model_id = resolve_model_id(self.cheap_model_id, provider="openai")
        self.frontier_model_id = resolve_model_id(
            self.frontier_model_id, provider="openai"
        )
        self.base_url = normalize_openai_base_url(self.base_url)

    def model_id_for(self, tier: Tier) -> str:
        if tier is Tier.CHEAP:
            return self.cheap_model_id
        if tier is Tier.FRONTIER:
            return self.frontier_model_id
        raise ValueError(f"unknown tier: {tier!r}")

    def set_model_id(self, tier: Tier, spec: str) -> str:
        mid = resolve_model_id(spec, provider="openai")
        if tier is Tier.CHEAP:
            self.cheap_model_id = mid
        elif tier is Tier.FRONTIER:
            self.frontier_model_id = mid
        else:
            raise ValueError(f"unknown tier: {tier!r}")
        return mid

    def respond(
        self,
        history: list[HistoryItem],
        tools: list[dict],
        *,
        tier: Tier,
    ) -> Turn:
        payload: dict = {
            "model": self.model_id_for(tier),
            "max_tokens": self.max_tokens,
            "messages": _history_to_openai_messages(
                history, system_prompt=self.system_prompt
            ),
        }
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        if tools:
            payload["tools"] = _tools_to_openai(tools)
            payload["tool_choice"] = "auto"
        url = f"{self.base_url}/chat/completions"
        data = _post_chat_completions(
            url, payload, api_key=self.api_key, timeout_s=self.timeout_s
        )
        return _parse_openai_response(data)

    def complete(self, prompt: str, *, tier: Tier) -> str:
        turn = self.respond([UserMsg(prompt)], tools=[], tier=tier)
        if isinstance(turn, AssistantText):
            return turn.text
        raise RuntimeError("complete() expected a text turn, got tool_use")


@dataclass
class ModelRouter:
    """Tier-routing policy wrapper. Delegates to the configured live provider."""

    cheap_model: str | None = None
    frontier_model: str | None = None
    _provider: AnthropicModel | OpenAICompatibleModel = field(init=False, repr=False)

    def __post_init__(self) -> None:
        kwargs: dict = {}
        if self.cheap_model:
            kwargs["cheap_model_id"] = self.cheap_model
        if self.frontier_model:
            kwargs["frontier_model_id"] = self.frontier_model
        kind = live_provider()
        if kind == "openai":
            self._provider = OpenAICompatibleModel(**kwargs)
        elif kind == "anthropic":
            self._provider = AnthropicModel(**kwargs)
        else:
            raise RuntimeError(
                "no live LLM provider configured. Set OPENAI_BASE_URL or "
                "ANTHROPIC_API_KEY."
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
