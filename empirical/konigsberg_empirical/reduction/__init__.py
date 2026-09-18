"""Reduction / forbidden-configuration machinery (BK attack)."""

from .reducible import (
    BRIDGE_LEMMA,
    BRIDGE_TAG,
    Configuration,
    ReduceResult,
    ToolBudgetExceeded,
    bridge_is_formalized,
    build_configuration,
    forbidden_configuration_statement,
    reducible,
)
from .seeds import ReducibleSeed, load_reducible_seeds, next_unminted_seed

__all__ = [
    "BRIDGE_LEMMA",
    "BRIDGE_TAG",
    "Configuration",
    "ReduceResult",
    "ReducibleSeed",
    "ToolBudgetExceeded",
    "bridge_is_formalized",
    "build_configuration",
    "forbidden_configuration_statement",
    "load_reducible_seeds",
    "next_unminted_seed",
    "reducible",
]
