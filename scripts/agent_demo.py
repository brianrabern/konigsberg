#!/usr/bin/env python3
"""End-to-end agent demo: model → native tool use → provenance-stamped ledger.

Uses a real `AnthropicModel` when `ANTHROPIC_API_KEY` is set; otherwise a
scripted fake. Prefer `verify_coloring` when a Lean REPL is live (the honest
empirical→formal crossing); otherwise `choosability_refute` (needs the `sat`
extra) or `alon_tarsi` (pure Python).

Run:  uv run python scripts/agent_demo.py
"""
from __future__ import annotations

import os
import sys

from konigsberg_harness.agent import Agent, AgentConfig
from konigsberg_harness.models import AssistantText, HistoryItem, Tier, ToolCall
from konigsberg_harness.tools.registry import build_registry


class ScriptedDemoModel:
    """Offline stand-in: queued ToolCall / AssistantText turns."""

    def __init__(self, responses: list) -> None:
        self._q = list(responses)

    def respond(self, history: list[HistoryItem], tools: list[dict], *, tier: Tier):
        if not self._q:
            return AssistantText("(scripted model exhausted)")
        return self._q.pop(0)


def _scripted_plan(has_lean: bool, has_sat: bool) -> tuple[str, list]:
    """Return (task, queued model turns) for the offline path."""
    if has_lean:
        task = (
            "Verify that the path P3 (graph6 Bg) admits the proper coloring "
            "[0, 1, 0] via verify_coloring, then summarize."
        )
        turns = [
            [
                ToolCall(
                    id="call_1",
                    name="verify_coloring",
                    args={"graph6": "Bg", "coloring": [0, 1, 0]},
                )
            ],
            AssistantText("P3 coloring [0,1,0] is kernel-checked (proved)"),
        ]
        return task, turns
    if has_sat:
        task = (
            "Decide whether the cycle C5 (graph6 Dhc) is 2-choosable and record "
            "the result via choosability_refute, then summarize."
        )
        turns = [
            [
                ToolCall(
                    id="call_1",
                    name="choosability_refute",
                    args={"graph6": "Dhc", "k": 2},
                )
            ],
            AssistantText("C5 is not 2-choosable (certificate-checked)"),
        ]
        return task, turns
    task = (
        "Run alon_tarsi on the path P3 (graph6 Bg) and record the Claim, then summarize."
    )
    turns = [
        [ToolCall(id="call_1", name="alon_tarsi", args={"graph6": "Bg"})],
        AssistantText("alon_tarsi result recorded"),
    ]
    return task, turns


def _build_model(scripted_turns: list):
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            from konigsberg_harness.models import AnthropicModel

            model = AnthropicModel()
            print("model: AnthropicModel (ANTHROPIC_API_KEY present)")
            return model
        except RuntimeError as e:
            print(f"model: falling back to scripted ({e})")
    else:
        print("model: ScriptedDemoModel (set ANTHROPIC_API_KEY for a live run)")
    return ScriptedDemoModel(scripted_turns)


def main() -> int:
    from konigsberg_harness.repl import lean_toolchain_available, open_lean_repl

    lean_built = lean_toolchain_available()
    repl = open_lean_repl(timeout_s=180) if lean_built else None
    if repl is not None:
        print("repl: live LeanREPL")
    else:
        print("repl: none (formal/.lake missing — empirical tools only)")

    try:
        from konigsberg_empirical.coloring import choosability as ch

        has_sat = ch.is_available()
        task, scripted = _scripted_plan(has_lean=lean_built, has_sat=has_sat)
        reg = build_registry(repl)
        model = _build_model(scripted)
        agent = Agent(reg, model, AgentConfig(max_steps=8))
        print(f"task: {task}")
        result = agent.run(task)
        print("--- transcript ---")
        for o in result.transcript:
            tag = "ERR" if o.is_error else "ok"
            print(f"[{tag}] {o.action!r} -> {o.result}")
        print("--- ledger ---")
        print(result.ledger.render() or "(empty)")
        print(f"--- final ({result.steps} steps) ---")
        print(result.final)
        return 0 if result.ledger.claims() or result.final else 1
    finally:
        if repl is not None:
            repl.close()


if __name__ == "__main__":
    sys.exit(main())
