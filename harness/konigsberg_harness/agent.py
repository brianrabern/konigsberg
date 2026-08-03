"""The agent loop.

Deliberately a simple while-loop over a rich tool registry. No orchestration
graphs, no multi-agent architecture in v1 (add only when measurably justified).

The loop proposes tool calls; tools mint ledger Claims. The model can be as
creative and unreliable as it likes because acceptance is mechanical: a Claim's
trust root is stamped by the tool that produced it, never chosen by the model.
"""
from __future__ import annotations

from dataclasses import dataclass

from .ledger import Ledger
from .models import ModelRouter, Tier
from .tools.registry import ToolRegistry


@dataclass
class AgentConfig:
    max_steps: int = 40


class Agent:
    def __init__(self, registry: ToolRegistry, router: ModelRouter, config: AgentConfig | None = None) -> None:
        self.registry = registry
        self.router = router
        self.ledger = Ledger()
        self.config = config or AgentConfig()

    def run(self, task: str) -> Ledger:
        for _step in range(self.config.max_steps):
            # 1. Ask the model for the next action given task + surfaced context.
            # 2. Parse a tool call; dispatch through the registry.
            # 3. Tool returns a Claim (already provenance-stamped) -> ledger.record.
            # 4. Stop when the model emits a terminal answer.
            raise NotImplementedError("wire model.complete -> parse -> registry.dispatch")
        return self.ledger
