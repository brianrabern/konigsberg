"""Pydantic arg models for model-callable tools.

Each model is the single source of truth for a tool's JSON schema (API
`input_schema`) and for validating args before dispatch.
"""
from __future__ import annotations

from pydantic import BaseModel


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


class LiteratureSearchArgs(BaseModel):
    query: str
    area: str | None = None
    status: str | None = None


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


# Empty schema placeholder for tools registered without an args model (code-only).
EMPTY_OBJECT_SCHEMA: dict = {"type": "object", "properties": {}}


def schema_for(model: type[BaseModel] | None) -> dict:
    if model is None:
        return dict(EMPTY_OBJECT_SCHEMA)
    # mode='serialization' keeps JSON-schema JSON-native for the API.
    return model.model_json_schema()
