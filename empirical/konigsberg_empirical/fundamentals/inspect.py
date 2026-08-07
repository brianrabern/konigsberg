"""describe_graph overview + generators."""
from __future__ import annotations

from typing import Any

from ..core import Graph
from . import invariants as inv


def describe(g: Graph) -> dict[str, Any]:
    """Cheap one-shot overview (no NP-hard establishment)."""
    degs = inv.degree_sequence(g)
    bip, parts = inv.is_bipartite(g)
    planar, _ = inv.is_planar(g)
    degner, _ = inv.degeneracy(g)
    named = inv.overview_named(g)
    return {
        "n": g.n,
        "m": len(g.edges),
        "degree_sequence": degs,
        "delta": inv.min_degree(g),
        "Delta": inv.max_degree(g),
        "average_degree": round(inv.average_degree(g), 6),
        "density": round(inv.density(g), 6),
        "connected": inv.is_connected(g),
        "num_components": inv.num_components(g),
        "bipartite": bip,
        "bipartition": parts,
        "girth": inv.girth(g),
        "is_tree": inv.is_tree(g),
        "is_forest": inv.is_forest(g),
        "is_regular": inv.is_regular(g),
        "is_planar": planar,
        "degeneracy": degner,
        "named": named,
    }
