"""Graph fundamentals: construction, IO, invariants, ops, relations, paths.

Domain-agnostic substrate. networkx does the algorithms; we own the graph6
canonical handle and certificate extraction for the ledger.
"""
from __future__ import annotations

from . import invariants, ops, paths, relations
from .codec import (
    canonical_graph6,
    graph6_decode,
    graph6_encode,
    to_graph6,
    to_nx,
)
from .construct import make_graph as build_graph
from .generate import enumerate_graph6, random_gnp
from .inspect import describe

__all__ = [
    "build_graph",
    "canonical_graph6",
    "describe",
    "enumerate_graph6",
    "graph6_decode",
    "graph6_encode",
    "invariants",
    "ops",
    "paths",
    "random_gnp",
    "relations",
    "to_graph6",
    "to_nx",
]
