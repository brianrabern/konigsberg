"""Provider routing (open decision #5).

Policy sketch: cheap models dispatch empirical tools and triage; a frontier model
drives proof search. Thresholds TBD and belong behind this interface so the loop
never hard-codes a provider. Never read API keys from anywhere but the
environment.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class Tier(Enum):
    CHEAP = "cheap"      # empirical dispatch, routing, summarization
    FRONTIER = "frontier"  # proof search, hard lemma decomposition


class Model(Protocol):
    """What the agent loop needs from a model. Any provider (or a test fake)
    satisfies this; the loop never depends on a concrete SDK."""

    def complete(self, prompt: str, *, tier: Tier) -> str: ...


@dataclass
class ModelRouter:
    cheap_model: str = "TBD"
    frontier_model: str = "TBD"

    def complete(self, prompt: str, *, tier: Tier) -> str:
        raise NotImplementedError("wire to provider SDK behind this interface")
