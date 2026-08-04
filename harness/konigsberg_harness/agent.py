"""The agent loop.

Deliberately a simple while-loop over a rich tool registry. No orchestration
graphs, no multi-agent architecture in v1 (add only when measurably justified).

The loop proposes tool calls; tools mint ledger Claims. The model can be as
creative and unreliable as it likes because acceptance is mechanical: a Claim's
trust root is stamped by the tool that produced it, never chosen by the model. A
model that merely *asserts* "I proved it" in a `final` message mints nothing —
only a tool result becomes a Claim.

Action protocol — the model emits ONE JSON object per turn:

    {"tool": "<name>", "args": {...}}   # dispatch a registered tool
    {"final": "<answer>"}               # stop

Tool arguments must be JSON (strings/numbers/lists/dicts). Tools whose arguments
are not serializable (e.g. counterexample_search's Python predicate) are called
directly in code, not exposed to the model — see tools.registry.build_registry.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from .ledger import Claim, Ledger
from .models import Model, Tier
from .tools.registry import ToolRegistry


@dataclass
class AgentConfig:
    max_steps: int = 40


@dataclass
class Observation:
    """One loop turn: the action taken and the resulting observation text."""

    action: object
    result: str
    is_error: bool = False


@dataclass
class AgentResult:
    final: str | None
    ledger: Ledger
    steps: int
    transcript: list[Observation] = field(default_factory=list)


def _parse_action(text: str) -> dict:
    """Parse the model's turn into an action dict. Tolerates ``` code fences."""
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("`").strip()
        if s.lower().startswith("json"):
            s = s[4:].strip()
    try:
        obj = json.loads(s)
    except json.JSONDecodeError as e:
        raise ValueError(f"not valid JSON: {e}") from e
    if not isinstance(obj, dict):
        # ValueError (not TypeError) on purpose: the loop treats every malformed
        # action the same way, via one `except ValueError`.
        raise ValueError("action must be a JSON object")  # noqa: TRY004
    return obj


def _render_result(result: object) -> str:
    if isinstance(result, list):
        return "results: " + ("; ".join(map(str, result)) if result else "(none)")
    return str(result)


def _render_prompt(task: str, tools: list[dict[str, str]], transcript: list[Observation]) -> str:
    lines = [f"TASK: {task}", "", "TOOLS:"]
    lines += [f"- {t['name']}: {t['doc']}" for t in tools]
    lines += [
        "",
        (
            'Respond with ONE JSON object: {"tool": name, "args": {...}} to act, '
            'or {"final": answer} to finish.'
        ),
    ]
    if transcript:
        lines += ["", "HISTORY:"]
        lines += [f"* {o.action} -> {o.result}" for o in transcript]
    return "\n".join(lines)


class Agent:
    def __init__(
        self, registry: ToolRegistry, model: Model, config: AgentConfig | None = None
    ) -> None:
        self.registry = registry
        self.model = model
        self.ledger = Ledger()
        self.config = config or AgentConfig()

    def run(self, task: str) -> AgentResult:
        transcript: list[Observation] = []
        final: str | None = None
        steps = 0

        for _ in range(self.config.max_steps):
            steps += 1
            prompt = _render_prompt(task, self.registry.spec(), transcript)
            raw = self.model.complete(prompt, tier=Tier.FRONTIER)

            try:
                action = _parse_action(raw)
            except ValueError as e:
                transcript.append(Observation(raw, f"ERROR unparseable action: {e}", is_error=True))
                continue

            if "final" in action:
                final = action["final"]
                break

            name = action.get("tool")
            if not name:
                transcript.append(
                    Observation(action, "ERROR action has neither 'tool' nor 'final'", is_error=True)
                )
                continue

            args = action.get("args") or {}
            try:
                result = self.registry.dispatch(name, **args)
            except Exception as e:  # noqa: BLE001 — any tool failure becomes an observation, not a crash
                transcript.append(Observation(action, f"ERROR {type(e).__name__}: {e}", is_error=True))
                continue

            # ONLY a tool-minted Claim enters the ledger. Model text never does.
            if isinstance(result, Claim):
                self.ledger.record(result)
                transcript.append(Observation(action, result.render()))
            else:
                transcript.append(Observation(action, _render_result(result)))

        return AgentResult(final=final, ledger=self.ledger, steps=steps, transcript=transcript)
