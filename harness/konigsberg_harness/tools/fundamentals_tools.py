"""Graph-theory fundamentals tools (Lean-free). Trust: python-checked / certificate.

graph6 is the universal handle. ``make_graph`` mints canonical graph6; the agent
must never hand-write one. NP-hard invariants always carry a re-checkable witness.
"""
from __future__ import annotations

from typing import Any

from konigsberg_empirical.fundamentals import (
    build_graph,
    canonical_graph6,
    describe,
    enumerate_graph6,
    ops,
    paths,
    random_gnp,
)
from konigsberg_empirical.fundamentals import (
    graph6_decode as _decode,
)
from konigsberg_empirical.fundamentals import (
    graph6_encode as _encode,
)
from konigsberg_empirical.fundamentals import (
    invariants as inv,
)
from konigsberg_empirical.fundamentals import (
    relations as rel,
)
from konigsberg_empirical.search.enumerate import parse_graph6

from ..ledger import Claim, mint_certificate, mint_enumeration


def _pc(statement: str, *, tool: str, bound: str = "deterministic") -> Claim:
    """Polynomial / deterministic invariant → python-checked (ENUMERATION root)."""
    return mint_enumeration(statement, bound=bound, exhaustive=True, tool=tool)


def _g(graph6: str):
    return parse_graph6(graph6)


def _out_graph(g, *, tool: str, label: str) -> Claim:
    g6 = canonical_graph6(g)
    return _pc(
        f"{label} → graph6={g6} (n={g.n}, m={len(g.edges)})",
        tool=tool,
        bound=f"n={g.n}",
    )


# --- WP1 construction & IO ------------------------------------------------


def make_graph(
    kind: str,
    n: int | None = None,
    m: int | None = None,
    r: int | None = None,
    d: int | None = None,
    parts: list[int] | None = None,
    edges: list[list[int]] | None = None,
    graph6: str | None = None,
) -> Claim:
    """Mint a canonical graph6 from a named family or explicit edges/graph6.

    The only approved way to obtain a graph6 handle — never invent one by hand.
    Canonicalization uses nauty labelg when available; otherwise a documented
    near-canonical fallback (exact identity via is_isomorphic).
    """
    g = build_graph(
        kind,
        n=n,
        m=m,
        r=r,
        d=d,
        parts=parts,
        edges=edges,
        graph6=graph6,
    )
    g6 = canonical_graph6(g)
    return _pc(
        f"make_graph({kind}) → graph6={g6} (n={g.n}, m={len(g.edges)})",
        tool="make_graph",
        bound=f"n={g.n}",
    )


def graph6_encode(n: int, edges: list[list[int]]) -> Claim:
    """Encode n + edge list as graph6 (not necessarily canonical)."""
    s = _encode(n, edges)
    return _pc(f"graph6_encode → {s} (n={n}, m={len(edges)})", tool="graph6_encode")


def graph6_decode(graph6: str) -> Claim:
    """Decode graph6 → {n, edges}."""
    data = _decode(graph6)
    return _pc(
        f"graph6_decode({graph6!r}) → n={data['n']}, edges={data['edges']}",
        tool="graph6_decode",
        bound=f"n={data['n']}",
    )


# --- WP2 inspection -------------------------------------------------------


def describe_graph(graph6: str) -> Claim:
    """One-shot cheap overview. Default first move on an unfamiliar graph6."""
    g = _g(graph6)
    d = describe(g)
    named = d.get("named") or "unknown"
    return _pc(
        f"describe {graph6}: n={d['n']} m={d['m']} deg={d['degree_sequence']} "
        f"δ={d['delta']} Δ={d['Delta']} avg={d['average_degree']} dens={d['density']} "
        f"connected={d['connected']} #comp={d['num_components']} bipartite={d['bipartite']} "
        f"girth={d['girth']} tree={d['is_tree']} forest={d['is_forest']} "
        f"regular={d['is_regular']} planar={d['is_planar']} degeneracy={d['degeneracy']} "
        f"named={named}",
        tool="describe_graph",
        bound=f"n={g.n}",
    )


# --- WP3 invariants -------------------------------------------------------


def order(graph6: str) -> Claim:
    g = _g(graph6)
    return _pc(f"{graph6} has order n={g.n}", tool="order", bound=f"n={g.n}")


def size(graph6: str) -> Claim:
    g = _g(graph6)
    m = len(g.edges)
    return _pc(f"{graph6} has size m={m}", tool="size", bound=f"n={g.n}")


def degree_sequence(graph6: str) -> Claim:
    g = _g(graph6)
    degs = inv.degree_sequence(g)
    return _pc(
        f"{graph6} degree sequence {degs}",
        tool="degree_sequence",
        bound=f"n={g.n}",
    )


def min_degree(graph6: str) -> Claim:
    g = _g(graph6)
    return _pc(
        f"{graph6} has δ={inv.min_degree(g)} (degrees {inv.degree_sequence(g)})",
        tool="min_degree",
        bound=f"n={g.n}",
    )


def average_degree(graph6: str) -> Claim:
    g = _g(graph6)
    return _pc(
        f"{graph6} has average degree {inv.average_degree(g)}",
        tool="average_degree",
        bound=f"n={g.n}",
    )


def is_connected(graph6: str) -> Claim:
    g = _g(graph6)
    return _pc(
        f"{graph6} is_connected={inv.is_connected(g)}",
        tool="is_connected",
        bound=f"n={g.n}",
    )


def num_components(graph6: str) -> Claim:
    g = _g(graph6)
    return _pc(
        f"{graph6} has {inv.num_components(g)} connected components",
        tool="num_components",
        bound=f"n={g.n}",
    )


def components(graph6: str) -> Claim:
    g = _g(graph6)
    comps = inv.components(g)
    return _pc(
        f"{graph6} components={comps}",
        tool="components",
        bound=f"n={g.n}",
    )


def vertex_connectivity(graph6: str) -> Claim:
    g = _g(graph6)
    return _pc(
        f"{graph6} has κ={inv.vertex_connectivity(g)}",
        tool="vertex_connectivity",
        bound=f"n={g.n}",
    )


def edge_connectivity(graph6: str) -> Claim:
    g = _g(graph6)
    return _pc(
        f"{graph6} has λ={inv.edge_connectivity(g)}",
        tool="edge_connectivity",
        bound=f"n={g.n}",
    )


def is_k_connected(graph6: str, k: int) -> Claim:
    g = _g(graph6)
    ok = inv.is_k_connected(g, k)
    return _pc(
        f"{graph6} is_{k}_connected={ok} (κ={inv.vertex_connectivity(g)})",
        tool="is_k_connected",
        bound=f"n={g.n}",
    )


def is_bipartite(graph6: str) -> Claim:
    g = _g(graph6)
    ok, parts = inv.is_bipartite(g)
    if ok:
        return mint_certificate(
            f"{graph6} is bipartite (bipartition {parts})",
            checker="fundamentals.is_bipartite",
            tool="is_bipartite",
        )
    return _pc(f"{graph6} is not bipartite", tool="is_bipartite", bound=f"n={g.n}")


def girth(graph6: str) -> Claim:
    g = _g(graph6)
    gi = inv.girth(g)
    return _pc(f"{graph6} has girth={gi}", tool="girth", bound=f"n={g.n}")


def diameter(graph6: str) -> Claim:
    g = _g(graph6)
    return _pc(f"{graph6} has diameter={inv.diameter(g)}", tool="diameter", bound=f"n={g.n}")


def radius(graph6: str) -> Claim:
    g = _g(graph6)
    return _pc(f"{graph6} has radius={inv.radius(g)}", tool="radius", bound=f"n={g.n}")


def eccentricity(graph6: str) -> Claim:
    g = _g(graph6)
    return _pc(
        f"{graph6} eccentricity={inv.eccentricity(g)}",
        tool="eccentricity",
        bound=f"n={g.n}",
    )


def is_tree(graph6: str) -> Claim:
    g = _g(graph6)
    return _pc(f"{graph6} is_tree={inv.is_tree(g)}", tool="is_tree", bound=f"n={g.n}")


def is_forest(graph6: str) -> Claim:
    g = _g(graph6)
    return _pc(f"{graph6} is_forest={inv.is_forest(g)}", tool="is_forest", bound=f"n={g.n}")


def is_regular(graph6: str) -> Claim:
    g = _g(graph6)
    return _pc(
        f"{graph6} is_regular={inv.is_regular(g)} (degrees {inv.degree_sequence(g)})",
        tool="is_regular",
        bound=f"n={g.n}",
    )


def is_planar(graph6: str) -> Claim:
    g = _g(graph6)
    ok, kur = inv.is_planar(g)
    if ok:
        return _pc(f"{graph6} is planar", tool="is_planar", bound=f"n={g.n}")
    return mint_certificate(
        f"{graph6} is not planar (Kuratowski vertices {kur})",
        checker="networkx.check_planarity",
        tool="is_planar",
    )


def is_eulerian(graph6: str) -> Claim:
    g = _g(graph6)
    return _pc(
        f"{graph6} is_eulerian={inv.is_eulerian(g)}",
        tool="is_eulerian",
        bound=f"n={g.n}",
    )


def has_eulerian_path(graph6: str) -> Claim:
    g = _g(graph6)
    return _pc(
        f"{graph6} has_eulerian_path={inv.has_eulerian_path(g)}",
        tool="has_eulerian_path",
        bound=f"n={g.n}",
    )


def triangle_count(graph6: str) -> Claim:
    g = _g(graph6)
    return _pc(
        f"{graph6} has {inv.triangle_count(g)} triangles",
        tool="triangle_count",
        bound=f"n={g.n}",
    )


def transitivity(graph6: str) -> Claim:
    g = _g(graph6)
    return _pc(
        f"{graph6} has transitivity={inv.transitivity(g)}",
        tool="transitivity",
        bound=f"n={g.n}",
    )


def degeneracy(graph6: str) -> Claim:
    g = _g(graph6)
    d, ordering = inv.degeneracy(g)
    return mint_certificate(
        f"{graph6} has degeneracy={d} (elimination order {ordering})",
        checker="fundamentals.degeneracy",
        tool="degeneracy",
    )


def k_core_number(graph6: str) -> Claim:
    g = _g(graph6)
    return _pc(
        f"{graph6} has k-core number={inv.k_core_number(g)}",
        tool="k_core_number",
        bound=f"n={g.n}",
    )


def independence_number(graph6: str) -> Claim:
    g = _g(graph6)
    alpha, indset = inv.independence_number(g)
    if not inv.verify_independent_set(g, indset) or len(indset) != alpha:
        raise ValueError("independence witness failed independent check")
    return mint_certificate(
        f"{graph6} has α={alpha} (witnessing independent set {indset})",
        checker="fundamentals.verify_independent_set",
        tool="independence_number",
    )


def matching_number(graph6: str) -> Claim:
    g = _g(graph6)
    nu, matching = inv.matching_number(g)
    if not inv.verify_matching(g, matching) or len(matching) != nu:
        raise ValueError("matching witness failed independent check")
    return mint_certificate(
        f"{graph6} has ν={nu} (witnessing matching {matching})",
        checker="fundamentals.verify_matching",
        tool="matching_number",
    )


# --- WP4 structural ops ---------------------------------------------------


def complement(graph6: str) -> Claim:
    return _out_graph(ops.complement(_g(graph6)), tool="complement", label=f"complement({graph6})")


def induced_subgraph(graph6: str, vertices: list[int]) -> Claim:
    return _out_graph(
        ops.induced_subgraph(_g(graph6), vertices),
        tool="induced_subgraph",
        label=f"induced_subgraph({graph6}, {vertices})",
    )


def delete_vertex(graph6: str, v: int) -> Claim:
    return _out_graph(
        ops.delete_vertex(_g(graph6), v),
        tool="delete_vertex",
        label=f"delete_vertex({graph6}, {v})",
    )


def delete_vertices(graph6: str, vertices: list[int]) -> Claim:
    return _out_graph(
        ops.delete_vertices(_g(graph6), vertices),
        tool="delete_vertices",
        label=f"delete_vertices({graph6}, {vertices})",
    )


def delete_edge(graph6: str, u: int, v: int) -> Claim:
    return _out_graph(
        ops.delete_edge(_g(graph6), u, v),
        tool="delete_edge",
        label=f"delete_edge({graph6}, {u},{v})",
    )


def delete_edges(graph6: str, edges: list[list[int]]) -> Claim:
    return _out_graph(
        ops.delete_edges(_g(graph6), edges),
        tool="delete_edges",
        label=f"delete_edges({graph6}, {edges})",
    )


def add_edge(graph6: str, u: int, v: int) -> Claim:
    return _out_graph(
        ops.add_edge(_g(graph6), u, v),
        tool="add_edge",
        label=f"add_edge({graph6}, {u},{v})",
    )


def add_vertex(graph6: str) -> Claim:
    return _out_graph(ops.add_vertex(_g(graph6)), tool="add_vertex", label=f"add_vertex({graph6})")


def contract_edge(graph6: str, u: int, v: int) -> Claim:
    return _out_graph(
        ops.contract_edge(_g(graph6), u, v),
        tool="contract_edge",
        label=f"contract_edge({graph6}, {u},{v})",
    )


def line_graph(graph6: str) -> Claim:
    return _out_graph(ops.line_graph(_g(graph6)), tool="line_graph", label=f"line_graph({graph6})")


def independent_hitting_set(graph6: str) -> Claim:
    """Rabern's hitting property: does an independent set meet every maximum clique?

    True → certificate-checked (the witness independent hitting set is re-verified).
    False → python-checked (complete backtracking search; the property genuinely
    fails, e.g. C₅). ω and the number of maximum cliques are reported either way.
    """
    from konigsberg_empirical.fundamentals import hitting as _h

    g = _g(graph6)
    ok, witness = _h.independent_hitting_set(g)
    omega, qs = _h.maximum_cliques(g)
    if ok:
        if not _h.verify_independent_hitting_set(g, witness or []):
            raise ValueError("hitting-set witness failed independent re-check")
        return mint_certificate(
            f"{graph6}: independent set {witness} meets all {len(qs)} maximum "
            f"cliques (ω={omega}); re-checked. Rabern hitting property HOLDS.",
            checker="fundamentals.hitting.verify_independent_hitting_set",
            tool="independent_hitting_set",
        )
    return _pc(
        f"{graph6}: NO independent set meets all {len(qs)} maximum cliques "
        f"(ω={omega}); complete search. Rabern hitting property FAILS.",
        tool="independent_hitting_set",
        bound=f"n={g.n} exhaustive",
    )


def mycielskian(graph6: str) -> Claim:
    return _out_graph(
        ops.mycielskian(_g(graph6)), tool="mycielskian", label=f"mycielskian({graph6})"
    )


def blow_up(graph6: str, r: int, clique: bool = True) -> Claim:
    return _out_graph(
        ops.blow_up(_g(graph6), r, clique=clique),
        tool="blow_up",
        label=f"blow_up({graph6}, r={r}, clique={clique})",
    )


def disjoint_union(graph6: str, other: str) -> Claim:
    return _out_graph(
        ops.disjoint_union(_g(graph6), _g(other)),
        tool="disjoint_union",
        label=f"disjoint_union({graph6}, {other})",
    )


def union(graph6: str, other: str) -> Claim:
    return _out_graph(
        ops.union(_g(graph6), _g(other)),
        tool="union",
        label=f"union({graph6}, {other})",
    )


def join(graph6: str, other: str) -> Claim:
    return _out_graph(
        ops.join(_g(graph6), _g(other)),
        tool="join",
        label=f"join({graph6}, {other})",
    )


def cartesian_product(graph6: str, other: str) -> Claim:
    return _out_graph(
        ops.cartesian_product(_g(graph6), _g(other)),
        tool="cartesian_product",
        label=f"cartesian_product({graph6}, {other})",
    )


def tensor_product(graph6: str, other: str) -> Claim:
    return _out_graph(
        ops.tensor_product(_g(graph6), _g(other)),
        tool="tensor_product",
        label=f"tensor_product({graph6}, {other})",
    )


def k_core(graph6: str, k: int) -> Claim:
    return _out_graph(
        ops.k_core(_g(graph6), k),
        tool="k_core",
        label=f"k_core({graph6}, {k})",
    )


# --- WP5 relations --------------------------------------------------------


def is_isomorphic(graph6: str, other: str) -> Claim:
    g, h = _g(graph6), _g(other)
    ok = rel.is_isomorphic(g, h)
    return _pc(
        f"is_isomorphic({graph6}, {other})={ok}",
        tool="is_isomorphic",
        bound=f"n={g.n},{h.n}",
    )


def could_be_isomorphic(graph6: str, other: str) -> Claim:
    g, h = _g(graph6), _g(other)
    ok = rel.could_be_isomorphic(g, h)
    return _pc(
        f"could_be_isomorphic({graph6}, {other})={ok} (fast pre-check; True≠proof)",
        tool="could_be_isomorphic",
        bound=f"n={g.n},{h.n}",
    )


def is_subgraph(host: str, pattern: str) -> Claim:
    ok, emb = rel.is_subgraph(_g(host), _g(pattern))
    if ok:
        return mint_certificate(
            f"is_subgraph(host={host}, pattern={pattern})=True (embedding {emb})",
            checker="fundamentals.is_subgraph",
            tool="is_subgraph",
        )
    return _pc(
        f"is_subgraph(host={host}, pattern={pattern})=False",
        tool="is_subgraph",
    )


def is_induced_subgraph(host: str, pattern: str) -> Claim:
    ok, emb = rel.is_induced_subgraph(_g(host), _g(pattern))
    if ok:
        return mint_certificate(
            f"is_induced_subgraph(host={host}, pattern={pattern})=True (embedding {emb})",
            checker="fundamentals.is_induced_subgraph",
            tool="is_induced_subgraph",
        )
    return _pc(
        f"is_induced_subgraph(host={host}, pattern={pattern})=False",
        tool="is_induced_subgraph",
    )


def contains_clique(graph6: str, k: int) -> Claim:
    ok, wit = rel.contains_clique(_g(graph6), k)
    if ok:
        return mint_certificate(
            f"{graph6} contains K_{k} (witness {wit})",
            checker="list_checks.verify_clique",
            tool="contains_clique",
        )
    return _pc(f"{graph6} has no K_{k}", tool="contains_clique", bound=f"n={_g(graph6).n}")


def contains_cycle(graph6: str, length: int | None = None) -> Claim:
    ok, wit = rel.contains_cycle(_g(graph6), length)
    if ok:
        return mint_certificate(
            f"{graph6} contains cycle length={length if length is not None else 'any'} "
            f"(witness {wit})",
            checker="fundamentals.contains_cycle",
            tool="contains_cycle",
        )
    return _pc(
        f"{graph6} has no cycle" + (f" of length {length}" if length is not None else ""),
        tool="contains_cycle",
    )


def contains_path(graph6: str, length: int) -> Claim:
    ok, wit = rel.contains_path(_g(graph6), length)
    if ok:
        return mint_certificate(
            f"{graph6} contains path of length {length} (witness {wit})",
            checker="fundamentals.contains_path",
            tool="contains_path",
        )
    return _pc(
        f"{graph6} has no path of length {length}",
        tool="contains_path",
    )


def contains_minor(host: str, pattern: str) -> Claim:
    """Whether pattern is a minor of host, with branch-set witness when true.

    Not the same as is_subgraph: a False subgraph claim does not decide minors.
    """
    ok, branches = rel.contains_minor(_g(host), _g(pattern))
    if ok:
        if not rel.verify_minor_model(_g(host), _g(pattern), branches or []):
            raise ValueError("minor witness failed independent check")
        return mint_certificate(
            f"contains_minor(host={host}, pattern={pattern})=True "
            f"(branch sets {branches})",
            checker="fundamentals.verify_minor_model",
            tool="contains_minor",
        )
    return _pc(
        f"contains_minor(host={host}, pattern={pattern})=False "
        f"(no branch-set model; exhaustive for small n)",
        tool="contains_minor",
        bound=f"host_n={_g(host).n},pattern_n={_g(pattern).n}",
    )


# --- WP6 generators -------------------------------------------------------


def enumerate_graphs(
    n: int,
    connected: bool = False,
    min_degree: int | None = None,
    regular: int | None = None,
    max_hits: int | None = None,
) -> Claim:
    """Enumerate filtered graphs as canonical graph6. Uses geng when on PATH."""
    hits = enumerate_graph6(
        n,
        connected=connected,
        min_degree=min_degree,
        regular=regular,
        max_hits=max_hits,
    )
    return mint_enumeration(
        f"enumerate_graphs(n={n}, connected={connected}, min_degree={min_degree}, "
        f"regular={regular}, max_hits={max_hits}) → {len(hits)} graphs: {hits}",
        bound=f"n={n}",
        exhaustive=max_hits is None,
        tool="enumerate_graphs",
    )


def random_graph(n: int, p: float, seed: int | None = None) -> Claim:
    """G(n,p) sample — clearly a sample, not a search result."""
    g6 = random_gnp(n, p, seed=seed)
    return mint_enumeration(
        f"random_graph G({n},{p}) seed={seed} → graph6={g6} [sample, not exhaustive]",
        bound=f"n={n}",
        exhaustive=False,
        tool="random_graph",
    )


# --- WP7 paths ------------------------------------------------------------


def neighbors(graph6: str, v: int) -> Claim:
    g = _g(graph6)
    return _pc(
        f"{graph6} neighbors({v})={paths.neighbors(g, v)}",
        tool="neighbors",
        bound=f"n={g.n}",
    )


def distance(graph6: str, u: int, v: int) -> Claim:
    g = _g(graph6)
    return _pc(
        f"{graph6} distance({u},{v})={paths.distance(g, u, v)}",
        tool="distance",
        bound=f"n={g.n}",
    )


def shortest_path(graph6: str, u: int, v: int) -> Claim:
    g = _g(graph6)
    sp = paths.shortest_path(g, u, v)
    if sp is not None:
        return mint_certificate(
            f"{graph6} shortest_path({u},{v})={sp}",
            checker="networkx.shortest_path",
            tool="shortest_path",
        )
    return _pc(
        f"{graph6} shortest_path({u},{v})=None (no path)",
        tool="shortest_path",
        bound=f"n={g.n}",
    )


def bfs_order(graph6: str, root: int) -> Claim:
    g = _g(graph6)
    return _pc(
        f"{graph6} bfs_order(root={root})={paths.bfs_order(g, root)}",
        tool="bfs_order",
        bound=f"n={g.n}",
    )


def dfs_order(graph6: str, root: int) -> Claim:
    g = _g(graph6)
    return _pc(
        f"{graph6} dfs_order(root={root})={paths.dfs_order(g, root)}",
        tool="dfs_order",
        bound=f"n={g.n}",
    )


def spanning_tree(graph6: str) -> Claim:
    return _out_graph(
        paths.spanning_tree(_g(graph6)),
        tool="spanning_tree",
        label=f"spanning_tree({graph6})",
    )


# Category map for /tools grouping (name → category). Existing coloring/formal/
# literature tools are listed too so /tools can group the full registry.
TOOL_CATEGORY: dict[str, str] = {
    # construction
    "make_graph": "construction",
    "graph6_encode": "construction",
    "graph6_decode": "construction",
    # inspection
    "describe_graph": "inspection",
    # invariants
    "order": "invariants",
    "size": "invariants",
    "degree_sequence": "invariants",
    "min_degree": "invariants",
    "max_degree": "invariants",
    "average_degree": "invariants",
    "is_connected": "invariants",
    "num_components": "invariants",
    "components": "invariants",
    "vertex_connectivity": "invariants",
    "edge_connectivity": "invariants",
    "is_k_connected": "invariants",
    "is_bipartite": "invariants",
    "girth": "invariants",
    "diameter": "invariants",
    "radius": "invariants",
    "eccentricity": "invariants",
    "is_tree": "invariants",
    "is_forest": "invariants",
    "is_regular": "invariants",
    "is_planar": "invariants",
    "is_eulerian": "invariants",
    "has_eulerian_path": "invariants",
    "triangle_count": "invariants",
    "transitivity": "invariants",
    "degeneracy": "invariants",
    "k_core_number": "invariants",
    "independence_number": "invariants",
    "clique_number": "invariants",
    "matching_number": "invariants",
    # structure
    "complement": "structure",
    "induced_subgraph": "structure",
    "delete_vertex": "structure",
    "delete_vertices": "structure",
    "delete_edge": "structure",
    "delete_edges": "structure",
    "add_edge": "structure",
    "add_vertex": "structure",
    "contract_edge": "structure",
    "line_graph": "structure",
    "mycielskian": "structure",
    "blow_up": "structure",
    "independent_hitting_set": "relations",
    "disjoint_union": "structure",
    "union": "structure",
    "join": "structure",
    "cartesian_product": "structure",
    "tensor_product": "structure",
    "k_core": "structure",
    # relations
    "is_isomorphic": "relations",
    "could_be_isomorphic": "relations",
    "is_subgraph": "relations",
    "is_induced_subgraph": "relations",
    "contains_clique": "relations",
    "contains_cycle": "relations",
    "contains_path": "relations",
    "contains_minor": "relations",
    # generators
    "enumerate_graphs": "generators",
    "random_graph": "generators",
    "counterexample_search": "generators",
    "bk_search": "generators",
    # paths
    "neighbors": "paths",
    "distance": "paths",
    "shortest_path": "paths",
    "bfs_order": "paths",
    "dfs_order": "paths",
    "spanning_tree": "paths",
    # coloring
    "choosability_refute": "coloring",
    "alon_tarsi": "coloring",
    "fixer_breaker": "coloring",
    "decide_colorable": "coloring",
    "chromatic_number": "coloring",
    "bk_predicate": "coloring",
    "list_critical": "coloring",
    "verify_coloring": "coloring",
    "reducible_configuration": "reduction",
    "discharging_unavoidable": "reduction",
    "campaign_status": "reduction",
    # formal
    "lean_check": "formal",
    "lean_typecheck_statement": "formal",
    "lean_search": "formal",
    "lean_prove": "formal",
    "lean_add_to_library": "formal",
    "lemma_list": "formal",
    "lemma_read": "formal",
    "reset_env": "formal",
    "retract": "formal",
    # literature
    "literature_search": "literature",
    "arxiv_search": "literature",
}

CATEGORY_ORDER = (
    "construction",
    "inspection",
    "invariants",
    "structure",
    "relations",
    "generators",
    "paths",
    "coloring",
    "reduction",
    "formal",
    "literature",
    "other",
)


def category_for(name: str) -> str:
    return TOOL_CATEGORY.get(name, "other")


FUNDAMENTAL_TOOL_NAMES: frozenset[str] = frozenset(
    name
    for name, cat in TOOL_CATEGORY.items()
    if cat
    in {
        "construction",
        "inspection",
        "invariants",
        "structure",
        "relations",
        "generators",
        "paths",
    }
    and name
    not in {
        # colored / search tools that live in empirical_tools, not register_fundamentals
        "max_degree",
        "clique_number",
        "counterexample_search",
        "bk_search",
    }
)


def register_fundamentals(reg: Any) -> None:
    """Register all fundamentals tools on ``reg`` (a ToolRegistry)."""
    from .arg_models import (
        BlowUpArgs,
        ContainsCycleArgs,
        ContainsPathArgs,
        EdgesArgs,
        EdgeUVArgs,
        EnumerateGraphsArgs,
        Graph6Args,
        Graph6EncodeArgs,
        HostPatternArgs,
        KArgs,
        MakeGraphArgs,
        PathEndpointsArgs,
        RandomGraphArgs,
        RootArgs,
        TwoGraphArgs,
        VertexArgs,
        VerticesArgs,
    )

    specs: list[tuple[str, Any, str, type]] = [
        (
            "make_graph",
            make_graph,
            (
                "Mint canonical graph6 from a named family (complete/cycle/path/empty/"
                "star/wheel/complete_bipartite/complete_multipartite/hypercube/grid/"
                "petersen/turan) or from_edges / from_graph6. Never invent graph6 by hand."
            ),
            MakeGraphArgs,
        ),
        (
            "graph6_encode",
            graph6_encode,
            "Encode n + edge list as graph6 (not necessarily canonical).",
            Graph6EncodeArgs,
        ),
        (
            "graph6_decode",
            graph6_decode,
            "Decode graph6 → {n, edges}.",
            Graph6Args,
        ),
        (
            "describe_graph",
            describe_graph,
            (
                "One-shot cheap overview (n,m,degrees,connectivity,bipartite,girth,"
                "tree/forest/regular/planar,degeneracy,named). First move on unfamiliar graph6."
            ),
            Graph6Args,
        ),
        ("order", order, "Order n(G). python-checked.", Graph6Args),
        ("size", size, "Size m(G). python-checked.", Graph6Args),
        ("degree_sequence", degree_sequence, "Degree sequence. python-checked.", Graph6Args),
        ("min_degree", min_degree, "δ(G). python-checked.", Graph6Args),
        ("average_degree", average_degree, "Average degree. python-checked.", Graph6Args),
        ("is_connected", is_connected, "Connected? python-checked.", Graph6Args),
        ("num_components", num_components, "Number of components. python-checked.", Graph6Args),
        ("components", components, "Vertex sets of components. python-checked.", Graph6Args),
        (
            "vertex_connectivity",
            vertex_connectivity,
            "κ(G) vertex-connectivity. python-checked.",
            Graph6Args,
        ),
        (
            "edge_connectivity",
            edge_connectivity,
            "λ(G) edge-connectivity. python-checked.",
            Graph6Args,
        ),
        ("is_k_connected", is_k_connected, "κ(G) ≥ k? python-checked.", KArgs),
        (
            "is_bipartite",
            is_bipartite,
            "Bipartite? + bipartition witness when true.",
            Graph6Args,
        ),
        ("girth", girth, "Girth (shortest cycle), or None if acyclic.", Graph6Args),
        ("diameter", diameter, "Diameter (None if disconnected).", Graph6Args),
        ("radius", radius, "Radius (None if disconnected).", Graph6Args),
        ("eccentricity", eccentricity, "Per-vertex eccentricity map.", Graph6Args),
        ("is_tree", is_tree, "Is a tree?", Graph6Args),
        ("is_forest", is_forest, "Is a forest?", Graph6Args),
        ("is_regular", is_regular, "Is regular?", Graph6Args),
        (
            "is_planar",
            is_planar,
            "Planar? Kuratowski vertex witness when false.",
            Graph6Args,
        ),
        ("is_eulerian", is_eulerian, "Has an Euler circuit?", Graph6Args),
        ("has_eulerian_path", has_eulerian_path, "Has an Euler path? (Königsberg)", Graph6Args),
        ("triangle_count", triangle_count, "Number of triangles.", Graph6Args),
        ("transitivity", transitivity, "Global clustering / transitivity.", Graph6Args),
        (
            "degeneracy",
            degeneracy,
            "Degeneracy + elimination-order witness. Backbone of greedy color/choose bounds.",
            Graph6Args,
        ),
        ("k_core_number", k_core_number, "Maximum core number (= degeneracy).", Graph6Args),
        (
            "independence_number",
            independence_number,
            "α(G) + witnessing independent set. certificate-checked.",
            Graph6Args,
        ),
        (
            "matching_number",
            matching_number,
            "ν(G) + witnessing matching. certificate-checked.",
            Graph6Args,
        ),
        ("complement", complement, "Complement → canonical graph6.", Graph6Args),
        (
            "induced_subgraph",
            induced_subgraph,
            "Induced subgraph on vertices → canonical graph6.",
            VerticesArgs,
        ),
        ("delete_vertex", delete_vertex, "Delete one vertex → canonical graph6.", VertexArgs),
        (
            "delete_vertices",
            delete_vertices,
            "Delete vertices → canonical graph6.",
            VerticesArgs,
        ),
        ("delete_edge", delete_edge, "Delete one edge → canonical graph6.", EdgeUVArgs),
        ("delete_edges", delete_edges, "Delete edges → canonical graph6.", EdgesArgs),
        ("add_edge", add_edge, "Add an edge → canonical graph6.", EdgeUVArgs),
        ("add_vertex", add_vertex, "Add an isolated vertex → canonical graph6.", Graph6Args),
        ("contract_edge", contract_edge, "Contract an edge → canonical graph6.", EdgeUVArgs),
        ("line_graph", line_graph, "Line graph → canonical graph6.", Graph6Args),
        (
            "independent_hitting_set",
            independent_hitting_set,
            (
                "Rabern's property: does an independent set meet every MAXIMUM clique? "
                "Returns a re-checked witness (holds) or a complete-search negative "
                "(fails, e.g. C₅). ω and #max-cliques reported. Certificate-checked on "
                "a hit; the engine under the BK clique-structure theorems."
            ),
            Graph6Args,
        ),
        (
            "mycielskian",
            mycielskian,
            (
                "Mycielskian μ(G) → canonical graph6: raises χ by one while keeping the "
                "clique number fixed (triangle-free stays triangle-free). μ(C₅) is the "
                "Grötzsch graph; iterate from K₂ for the triangle-free k-chromatic family. "
                "Use to build a recalled construction, then verify it with a tool."
            ),
            Graph6Args,
        ),
        (
            "blow_up",
            blow_up,
            (
                "Blow up each vertex into r copies → canonical graph6. clique=True: each "
                "vertex → Kᵣ (clique blow-up); clique=False: → independent set. Adjacent "
                "vertices' copies are fully joined."
            ),
            BlowUpArgs,
        ),
        (
            "disjoint_union",
            disjoint_union,
            "Disjoint union of two graphs → canonical graph6.",
            TwoGraphArgs,
        ),
        ("union", union, "Edge-union on same vertex set → canonical graph6.", TwoGraphArgs),
        ("join", join, "Join of two graphs → canonical graph6.", TwoGraphArgs),
        (
            "cartesian_product",
            cartesian_product,
            "Cartesian product → canonical graph6.",
            TwoGraphArgs,
        ),
        (
            "tensor_product",
            tensor_product,
            "Tensor (categorical) product → canonical graph6.",
            TwoGraphArgs,
        ),
        ("k_core", k_core, "k-core subgraph → canonical graph6.", KArgs),
        (
            "is_isomorphic",
            is_isomorphic,
            "Exact VF2 isomorphism test between two graph6 strings.",
            TwoGraphArgs,
        ),
        (
            "could_be_isomorphic",
            could_be_isomorphic,
            "Fast invariant pre-check (True does not prove isomorphism).",
            TwoGraphArgs,
        ),
        (
            "is_subgraph",
            is_subgraph,
            (
                "Does pattern embed as a (not necessarily induced) subgraph of host? "
                "NOT a proxy for minor-containment — use contains_minor for minors "
                "(Kuratowski/Wagner). is_subgraph=False does not imply no minor."
            ),
            HostPatternArgs,
        ),
        (
            "is_induced_subgraph",
            is_induced_subgraph,
            "Does pattern embed as an induced subgraph of host?",
            HostPatternArgs,
        ),
        (
            "contains_clique",
            contains_clique,
            "Contains K_k? + witnessing clique when true.",
            KArgs,
        ),
        (
            "contains_cycle",
            contains_cycle,
            "Contains a cycle (optionally of given length)? + witness.",
            ContainsCycleArgs,
        ),
        (
            "contains_path",
            contains_path,
            "Contains a path with `length` edges? + witness.",
            ContainsPathArgs,
        ),
        (
            "contains_minor",
            contains_minor,
            (
                "Is pattern a minor of host? Returns branch-set witness when true "
                "(certificate-checked). Use for K5 / K3,3 / Wagner–Kuratowski reasoning. "
                "Do NOT substitute is_subgraph for this."
            ),
            HostPatternArgs,
        ),
        (
            "enumerate_graphs",
            enumerate_graphs,
            "Enumerate filtered graphs as canonical graph6 (geng when available).",
            EnumerateGraphsArgs,
        ),
        (
            "random_graph",
            random_graph,
            "Sample G(n,p) → canonical graph6 (sample, not a search).",
            RandomGraphArgs,
        ),
        ("neighbors", neighbors, "Open neighborhood of v.", VertexArgs),
        ("distance", distance, "Shortest-path distance u–v (None if unreachable).", PathEndpointsArgs),
        ("shortest_path", shortest_path, "A shortest u–v path, or None.", PathEndpointsArgs),
        ("bfs_order", bfs_order, "BFS vertex order from root.", RootArgs),
        ("dfs_order", dfs_order, "DFS vertex order from root.", RootArgs),
        ("spanning_tree", spanning_tree, "Spanning tree/forest → canonical graph6.", Graph6Args),
    ]
    for name, fn, doc, model in specs:
        reg.register(name, fn, doc, args_model=model)
