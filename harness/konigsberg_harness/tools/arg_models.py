"""Pydantic arg models for model-callable tools.

Each model is the single source of truth for a tool's JSON schema (API
`input_schema`) and for validating args before dispatch.
"""
from __future__ import annotations

from pydantic import BaseModel, field_validator


class ChoosabilityRefuteArgs(BaseModel):
    graph6: str
    k: int = 3
    palette: int | None = None


class AlonTarsiArgs(BaseModel):
    graph6: str


class FixerBreakerArgs(BaseModel):
    graph6: str
    list_sizes: list[int]


class VerifyColoringArgs(BaseModel):
    graph6: str
    coloring: list[int]


class DecideColorableArgs(BaseModel):
    graph6: str
    k: int


class Graph6Args(BaseModel):
    graph6: str


class BkPredicateArgs(BaseModel):
    graph6: str


class BkSearchArgs(BaseModel):
    n_max: int
    k: int = 3
    n_min: int = 6
    palette: int | None = None
    max_hits: int = 5


class ReedSweepArgs(BaseModel):
    n_min: int = 2
    n_max: int = 7
    connected: bool = True
    max_tight: int = 30


class LiteratureSearchArgs(BaseModel):
    query: str
    area: str | None = None
    status: str | None = None


class ArxivSearchArgs(BaseModel):
    query: str
    max_results: int = 5
    sort_by: str = "relevance"
    category: str | None = "math.CO"


class ListCriticalArgs(BaseModel):
    graph6: str
    m: int
    palette: int | None = None


class ReducibleConfigurationArgs(BaseModel):
    core: str
    degrees: dict[str, int] | list[int]
    D: int | None = None


class DischargeRule(BaseModel):
    from_deg: int
    to_pattern: str
    amount: int
    radius: int = 1


class DischargingArgs(BaseModel):
    """Model proposes μ and rules; the engine verifies. v1 is D = 9 only."""

    D: int
    mu: dict[str, int]
    rules: list[DischargeRule]
    forbidden: list[str]

    @field_validator("mu", mode="before")
    @classmethod
    def _stringify_mu_keys(cls, v: object) -> object:
        if isinstance(v, dict):
            return {str(k): int(val) for k, val in v.items()}
        return v


class DischargingCoverArgs(BaseModel):
    """Cover a v1 local type from the Rabern catalog via core_forced_in_type."""

    center_deg: int
    n_high: int
    n_low: int | None = None


class DischargingSearchArgs(BaseModel):
    """Guided search: minted catalog cover, then rule/μ mutations."""

    D: int = 9
    mu: dict[str, int]
    rules: list[DischargeRule]
    forbidden: list[str] | None = None
    max_iters: int = 12

    @field_validator("mu", mode="before")
    @classmethod
    def _stringify_mu_keys(cls, v: object) -> object:
        if isinstance(v, dict):
            return {str(k): int(val) for k, val in v.items()}
        return v


class LeanCheckArgs(BaseModel):
    snippet: str


class LeanTypecheckStatementArgs(BaseModel):
    statement: str


class LeanSearchArgs(BaseModel):
    goal: str
    tactic: str = "exact?"


class LeanProveArgs(BaseModel):
    lean_name: str
    snippet: str
    durable: bool = False


class LeanRetractArgs(BaseModel):
    name: str


class LemmaReadArgs(BaseModel):
    name: str


class EmptyArgs(BaseModel):
    """No parameters."""


class LeanAddToLibraryArgs(BaseModel):
    """Write-back args. ``confirmed`` is NOT model-exposed — REPL sets it."""

    lean_name: str
    snippet: str
    area: str = "coloring"
    citation: str
    informal_statement: str
    referee_report: dict
    sanity_snippet: str | None = None


# --- Graph fundamentals ---------------------------------------------------


class MakeGraphArgs(BaseModel):
    """Named family or explicit construction. Prefer this over inventing graph6."""

    kind: str
    n: int | None = None
    m: int | None = None
    r: int | None = None
    d: int | None = None
    parts: list[int] | None = None
    edges: list[list[int]] | None = None
    graph6: str | None = None
    other: str | None = None  # second graph6 when kind='join'


class Graph6EncodeArgs(BaseModel):
    n: int
    edges: list[list[int]]


class VerticesArgs(BaseModel):
    graph6: str
    vertices: list[int]


class VertexArgs(BaseModel):
    graph6: str
    v: int


class EdgeUVArgs(BaseModel):
    graph6: str
    u: int
    v: int


class EdgesArgs(BaseModel):
    graph6: str
    edges: list[list[int]]


class TwoGraphArgs(BaseModel):
    graph6: str
    other: str


class HostPatternArgs(BaseModel):
    host: str
    pattern: str


class KArgs(BaseModel):
    graph6: str
    k: int


class BlowUpArgs(BaseModel):
    graph6: str
    r: int
    clique: bool = True


class ContainsCycleArgs(BaseModel):
    graph6: str
    length: int | None = None


class ContainsPathArgs(BaseModel):
    graph6: str
    length: int


class EnumerateGraphsArgs(BaseModel):
    n: int
    connected: bool = False
    min_degree: int | None = None
    regular: int | None = None
    max_hits: int | None = None


class RandomGraphArgs(BaseModel):
    n: int
    p: float
    seed: int | None = None


class PathEndpointsArgs(BaseModel):
    graph6: str
    u: int
    v: int


class RootArgs(BaseModel):
    graph6: str
    root: int


# Empty schema placeholder for tools registered without an args model (code-only).
EMPTY_OBJECT_SCHEMA: dict = {"type": "object", "properties": {}}


def schema_for(model: type[BaseModel] | None) -> dict:
    if model is None:
        return dict(EMPTY_OBJECT_SCHEMA)
    # mode='serialization' keeps JSON-schema JSON-native for the API.
    return model.model_json_schema()
