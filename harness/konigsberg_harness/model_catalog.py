"""Model aliases — short names resolve to provider model IDs.

Anthropic: friendly names (``opus``, ``opus 4.8``, ``sonnet``, ``fable``) or
full IDs (``claude-opus-5``). Local OpenAI-compatible servers (llama.cpp, vLLM,
Ollama): the spec is passed through unchanged. Used by env defaults and the
REPL ``/model`` command.
"""

from __future__ import annotations

import re

# Current Claude API aliases (see Anthropic models overview). Prefer undated
# aliases where Anthropic publishes them; dated IDs still pass through unchanged.
_ALIAS_TO_ID: dict[str, str] = {
    # Mythos-class
    "fable": "claude-fable-5",
    "fable5": "claude-fable-5",
    "mythos": "claude-mythos-5",
    "mythos5": "claude-mythos-5",
    # Opus
    "opus": "claude-opus-5",
    "opus5": "claude-opus-5",
    "opus48": "claude-opus-4-8",
    "opus47": "claude-opus-4-7",
    "opus46": "claude-opus-4-6",
    "opus45": "claude-opus-4-5",
    # Sonnet
    "sonnet": "claude-sonnet-5",
    "sonnet5": "claude-sonnet-5",
    "sonnet46": "claude-sonnet-4-6",
    "sonnet45": "claude-sonnet-4-5",
    # Haiku / cheap tier
    "haiku": "claude-haiku-4-5",
    "haiku45": "claude-haiku-4-5",
    "fast": "claude-haiku-4-5",
}

# Shown by `/model list` — keep short and current.
_LIST_ROWS: tuple[tuple[str, str], ...] = (
    ("fable", "claude-fable-5"),
    ("opus", "claude-opus-5"),
    ("opus 4.8", "claude-opus-4-8"),
    ("opus 4.7", "claude-opus-4-7"),
    ("sonnet", "claude-sonnet-5"),
    ("sonnet 4.6", "claude-sonnet-4-6"),
    ("haiku", "claude-haiku-4-5"),
)


def normalize_model_key(spec: str) -> str:
    """``Opus 4.8`` / ``opus-4.8`` → ``opus48``."""
    return re.sub(r"[^a-z0-9]+", "", spec.strip().lower())


_LOCAL_PROVIDERS = frozenset({"openai", "local", "llama.cpp", "llamacpp"})


def resolve_model_id(spec: str, *, provider: str | None = None) -> str:
    """Resolve a friendly name or pass through a full provider id.

    Anthropic: aliases (``opus``) or a full ``claude-…`` id.
    Local OpenAI-compatible: any non-empty string (GGUF name, ``local``, …).

    Raises ``ValueError`` if ``spec`` is empty or an unknown Anthropic alias.
    """
    raw = spec.strip()
    if not raw:
        raise ValueError("empty model spec")
    kind = (provider or "").strip().lower()
    if kind in _LOCAL_PROVIDERS:
        return raw
    if raw.lower().startswith("claude-"):
        return raw
    key = normalize_model_key(raw)
    if key in _ALIAS_TO_ID:
        return _ALIAS_TO_ID[key]
    known = ", ".join(a for a, _ in _LIST_ROWS)
    raise ValueError(
        f"unknown model {spec!r} — use a full id (claude-…) or one of: {known}"
    )


def format_model_catalog(*, provider: str | None = None) -> str:
    kind = (provider or "anthropic").strip().lower()
    if kind in _LOCAL_PROVIDERS:
        return (
            "OpenAI-compatible local server (llama.cpp / vLLM / Ollama / LM Studio)\n"
            "  any id the server accepts — llama.cpp often ignores the name\n"
            "  when a single GGUF is loaded.\n"
            "  /model <id>           set chat model id\n"
            "  /model cheap <id>     set compaction model id\n"
            "  env: KONIGSBERG_MODEL, OPENAI_BASE_URL"
        )
    lines = ["short name → API id"]
    for short, mid in _LIST_ROWS:
        lines.append(f"  {short:<12} {mid}")
    lines.append("  (any claude-… id also accepted)")
    return "\n".join(lines)
