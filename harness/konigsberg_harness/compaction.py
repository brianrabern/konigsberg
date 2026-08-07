"""Context compaction — Claude Code's pipeline, ledger-safe.

Compaction may rewrite the *chat transcript* when it nears the context window.
It must **never** touch the Ledger: established claims survive verbatim; the
model always sees the full current trust state after older chat is summarized.
"""
from __future__ import annotations

from dataclasses import dataclass

from .models import (
    AssistantText,
    HistoryItem,
    Model,
    Tier,
    ToolCall,
    ToolResultMsg,
    UserMsg,
)
from .session import Session, SessionStore


def estimate_tokens(history: list[HistoryItem]) -> int:
    """Rough token estimate (chars/4). Good enough for a compaction trigger."""
    n = 0
    for item in history:
        if isinstance(item, (UserMsg, AssistantText)):
            n += len(item.text)
        elif isinstance(item, ToolCall):
            n += len(item.name) + len(str(item.args))
        elif isinstance(item, ToolResultMsg):
            n += len(item.content)
    return max(1, n // 4)


@dataclass
class CompactionConfig:
    """When estimated tokens exceed ``threshold``, compact to keep ``keep_recent``."""

    threshold: int = 80_000  # ~fraction of a typical context window
    keep_recent: int = 8


def should_compact(session: Session, config: CompactionConfig | None = None) -> bool:
    cfg = config or CompactionConfig()
    return estimate_tokens(session.history) >= cfg.threshold


def _kept_window(history: list[HistoryItem], keep_recent: int) -> list[HistoryItem]:
    """Last ``keep_recent`` items, expanded so we don't split a tool_use/result group."""
    if keep_recent <= 0 or len(history) <= keep_recent:
        return list(history)
    start = len(history) - keep_recent
    # If the window starts on a ToolResultMsg, walk back to include its ToolCall(s).
    while start > 0 and isinstance(history[start], ToolResultMsg):
        start -= 1
    # Include any contiguous ToolCall block immediately before results at the boundary.
    while start > 0 and isinstance(history[start - 1], ToolCall):
        start -= 1
    return list(history[start:])


def _summary_prompt(older: list[HistoryItem], ledger_render: str) -> str:
    lines = [
        "Summarize the earlier part of this graph-theory investigation for continuity.",
        "Be concise. Preserve: graphs considered, tool outcomes, open questions.",
        "Do NOT invent claims — trust state is recorded separately in the ledger.",
        "",
        "Ledger (authoritative; do not alter):",
        ledger_render or "(empty)",
        "",
        "Earlier transcript:",
    ]
    for item in older:
        if isinstance(item, UserMsg):
            lines.append(f"USER: {item.text}")
        elif isinstance(item, AssistantText):
            lines.append(f"ASSISTANT: {item.text}")
        elif isinstance(item, ToolCall):
            lines.append(f"TOOL_CALL {item.name}({item.args})")
        elif isinstance(item, ToolResultMsg):
            tag = "ERROR" if item.is_error else "OK"
            lines.append(f"TOOL_RESULT[{tag}]: {item.content[:500]}")
    lines.append("")
    lines.append("Reply with only the summary text.")
    return "\n".join(lines)


def compact(
    session: Session,
    model: Model,
    *,
    config: CompactionConfig | None = None,
    store: SessionStore | None = None,
) -> str:
    """Replace older history with a CHEAP-tier summary; ledger untouched.

    Returns the summary text. Raises if there is nothing to compact.
    """
    cfg = config or CompactionConfig()
    kept = _kept_window(session.history, cfg.keep_recent)
    older = session.history[: len(session.history) - len(kept)] if kept else list(session.history)
    if not older:
        return ""

    # Snapshot for the invariant: callers/tests compare ledger before/after.
    ledger_before = session.ledger.claims()

    prompt = _summary_prompt(older, session.ledger.render())
    turn = model.respond([UserMsg(prompt)], tools=[], tier=Tier.CHEAP)
    if not isinstance(turn, AssistantText):
        raise TypeError("compaction expected a text summary, got tool_use")
    summary = turn.text.strip() or "(empty summary)"
    summary_msg = f"Summary of earlier work:\n{summary}"

    if store is not None:
        store.log_compaction(session, summary=summary_msg, kept=kept)
    else:
        session.history = [UserMsg(summary_msg), *kept]
        session.touch()

    assert session.ledger.claims() == ledger_before, "compaction must not alter the ledger"
    return summary
