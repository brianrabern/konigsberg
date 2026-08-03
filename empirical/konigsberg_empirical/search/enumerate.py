"""Graph enumeration via nauty/geng with degree/connectivity constraints.

geng streams non-isomorphic graphs; we parse graph6 into core.Graph. Until the
nauty backend is wired, `all_graphs` raises so callers fail loudly rather than
silently enumerating nothing.
"""
from __future__ import annotations

from collections.abc import Iterator

from ..core import Graph


def all_graphs(n: int, *, constraints: dict | None = None) -> Iterator[Graph]:
    raise NotImplementedError("wire nauty/geng; parse graph6 -> core.Graph")
