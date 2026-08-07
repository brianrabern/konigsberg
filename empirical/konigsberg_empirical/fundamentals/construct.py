"""Named graph families and explicit constructors → core.Graph."""
from __future__ import annotations

from typing import Any

import networkx as nx

from ..core import Graph
from ..search.enumerate import parse_graph6
from .codec import from_nx

_FAMILIES = frozenset(
    {
        "complete",
        "cycle",
        "path",
        "empty",
        "star",
        "wheel",
        "complete_bipartite",
        "complete_multipartite",
        "hypercube",
        "grid",
        "petersen",
        "turan",
        "from_edges",
        "from_graph6",
    }
)


def make_graph(
    kind: str,
    *,
    n: int | None = None,
    m: int | None = None,
    r: int | None = None,
    d: int | None = None,
    parts: list[int] | None = None,
    edges: list[list[int] | tuple[int, int]] | None = None,
    graph6: str | None = None,
) -> Graph:
    """Build a simple Graph from a named family or explicit data.

    ``kind`` is one of the WP1 families / from_edges / from_graph6.
    """
    kind = kind.strip().lower().replace("-", "_").replace(" ", "_")
    if kind not in _FAMILIES:
        raise ValueError(f"unknown graph kind {kind!r}; want one of {sorted(_FAMILIES)}")

    if kind == "from_graph6":
        if not graph6:
            raise ValueError("from_graph6 requires graph6=")
        return parse_graph6(graph6)

    if kind == "from_edges":
        if n is None or edges is None:
            raise ValueError("from_edges requires n= and edges=")
        return Graph.of(n, edges)

    if kind == "petersen":
        return from_nx(nx.petersen_graph())

    if kind == "complete":
        if n is None:
            raise ValueError("complete requires n=")
        return from_nx(nx.complete_graph(n))

    if kind == "cycle":
        if n is None or n < 3:
            raise ValueError("cycle requires n≥3")
        return from_nx(nx.cycle_graph(n))

    if kind == "path":
        if n is None or n < 1:
            raise ValueError("path requires n≥1")
        return from_nx(nx.path_graph(n))

    if kind == "empty":
        if n is None:
            raise ValueError("empty requires n=")
        return Graph.of(n, [])

    if kind == "star":
        # star(n) = K_{1,n} with n leaves → n+1 vertices (networkx star_graph(n))
        if n is None:
            raise ValueError("star requires n= (number of leaves)")
        return from_nx(nx.star_graph(n))

    if kind == "wheel":
        if n is None or n < 4:
            raise ValueError("wheel requires n≥4 (hub + cycle)")
        return from_nx(nx.wheel_graph(n))

    if kind == "complete_bipartite":
        if n is None or m is None:
            raise ValueError("complete_bipartite requires m= and n=")
        return from_nx(nx.complete_bipartite_graph(m, n))

    if kind == "complete_multipartite":
        if not parts:
            raise ValueError("complete_multipartite requires parts=[...]")
        return from_nx(nx.complete_multipartite_graph(*parts))

    if kind == "hypercube":
        if d is None:
            raise ValueError("hypercube requires d=")
        return from_nx(nx.hypercube_graph(d))

    if kind == "grid":
        if m is None or n is None:
            raise ValueError("grid requires m= and n=")
        return from_nx(nx.grid_2d_graph(m, n))

    if kind == "turan":
        if n is None or r is None:
            raise ValueError("turan requires n= and r=")
        return from_nx(nx.turan_graph(n, r))

    raise ValueError(f"unhandled kind {kind!r}")  # pragma: no cover


def summary(graph: Graph) -> dict[str, Any]:
    return {"n": graph.n, "m": len(graph.edges)}
