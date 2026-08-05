"""Alon–Tarsi / Combinatorial Nullstellensatz.

Faithful port of WebGraphs orientation search (FindChoosables.CheckOrientation +
Graph.EnumerateOrientations / CountSpanningEulerianSubgraphs) on top of the
ported graph polynomial (polynomials.py).

An orientation with #even ≠ #odd spanning Eulerian subgraphs is a finite,
independently re-checkable certificate — so hits mint CERTIFICATE trust.
AT is *sufficient only*: failure proves nothing about choosability.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..core import Graph
from .polynomials import graph_polynomial_coefficient, sign_sum

__all__ = [
    "ATCertificate",
    "alon_tarsi_number",
    "certificate",
    "count_eulerian_subgraphs",
    "graph_polynomial_coefficient",
    "sign_sum",
    "verify_certificate",
]


# --- orientation helpers ----------------------------------------------------

@dataclass(frozen=True)
class ATCertificate:
    """AT-good orientation. `arcs` are directed edges u→v covering every edge of G."""

    arcs: frozenset[tuple[int, int]]
    even: int
    odd: int
    coefficient: int

    @property
    def out_degrees(self) -> tuple[int, ...]:
        if not self.arcs:
            return ()
        n = 1 + max(max(u, v) for u, v in self.arcs)
        out = [0] * n
        for u, _v in self.arcs:
            out[u] += 1
        return tuple(out)


def _out_degrees(arcs: list[tuple[int, int]] | frozenset[tuple[int, int]], n: int) -> list[int]:
    out = [0] * n
    for u, _v in arcs:
        out[u] += 1
    return out


def _in_degrees(arcs: list[tuple[int, int]] | frozenset[tuple[int, int]], n: int) -> list[int]:
    inn = [0] * n
    for _u, v in arcs:
        inn[v] += 1
    return inn


def count_eulerian_subgraphs(
    orientation: list[tuple[int, int]] | frozenset[tuple[int, int]],
    n: int | None = None,
) -> tuple[int, int]:
    """Count (even, odd) spanning Eulerian subdigraphs of a directed orientation.

    Port of Graph.CountSpanningEulerianSubgraphs: a spanning Eulerian subdigraph
    is a subset of arcs where every vertex has equal in- and out-degree; parity
    is by number of arcs. The empty subdigraph is even.
    """
    arcs = list(orientation)
    if n is None:
        n = 0 if not arcs else 1 + max(max(u, v) for u, v in arcs)
    m = len(arcs)
    even = odd = 0
    for mask in range(1 << m):
        out = [0] * n
        inn = [0] * n
        size = 0
        for i, (u, v) in enumerate(arcs):
            if mask & (1 << i):
                out[u] += 1
                inn[v] += 1
                size += 1
        if out == inn:
            if size % 2 == 0:
                even += 1
            else:
                odd += 1
    return even, odd


def _is_orientation_of(graph: Graph, arcs: frozenset[tuple[int, int]]) -> bool:
    if len(arcs) != len(graph.edges):
        return False
    seen: set[tuple[int, int]] = set()
    for u, v in arcs:
        e = (u, v) if u < v else (v, u)
        if e not in graph.edges or e in seen:
            return False
        seen.add(e)
    return len(seen) == len(graph.edges)


def _enumerate_orientations(
    graph: Graph, max_out: list[int]
) -> list[tuple[frozenset[tuple[int, int]], tuple[int, ...]]]:
    """Orientations with outdegree[v] <= max_out[v], deduped by in-degree sequence.

    Mirrors FindChoosables: EnumerateOrientations(v => Degree(v)+1-f(v)) yields
    orientations with outdeg <= f(v)-1; CheckOrientation skips duplicate
    InDegreeSequence.
    """
    edges = sorted(graph.edges)
    m = len(edges)
    n = graph.n
    seen_indeg: set[tuple[int, ...]] = set()
    results: list[tuple[frozenset[tuple[int, int]], tuple[int, ...]]] = []

    for mask in range(1 << m):
        arcs: list[tuple[int, int]] = []
        out = [0] * n
        for i, (u, v) in enumerate(edges):
            if mask & (1 << i):
                arcs.append((v, u))
                out[v] += 1
            else:
                arcs.append((u, v))
                out[u] += 1
        if any(out[v] > max_out[v] for v in range(n)):
            continue
        indeg = tuple(graph.degree(v) - out[v] for v in range(n))
        if indeg in seen_indeg:
            continue
        seen_indeg.add(indeg)
        results.append((frozenset(arcs), tuple(out)))
    return results


def _check_orientation(
    graph: Graph, arcs: frozenset[tuple[int, int]], outdeg: tuple[int, ...]
) -> ATCertificate | None:
    """AT-good iff coefficient ≠ 0 (≡ even ≠ odd).

    Search uses the coefficient route (cheap in the out-degree monomial support);
    Eulerian counts are computed once on a hit for the certificate witness and
    cross-checked against the coefficient.
    """
    coeff = graph_polynomial_coefficient(graph, list(outdeg))
    if coeff == 0:
        return None
    even, odd = count_eulerian_subgraphs(arcs, graph.n)
    if even == odd:
        raise RuntimeError(
            f"AT routes disagree: coeff={coeff}, even={even}, odd={odd} on {graph}"
        )
    return ATCertificate(arcs=arcs, even=even, odd=odd, coefficient=coeff)


def certificate(
    graph: Graph, f: list[int] | None = None
) -> ATCertificate | None:
    """Return an AT-good orientation with outdeg[v] < f[v], or None.

    If f is None, search for the smallest constant list-size k (= AT number) that
    admits a certificate.
    """
    if graph.n == 0:
        return ATCertificate(arcs=frozenset(), even=1, odd=0, coefficient=1)

    if f is None:
        # AT(G) <= Δ+1 always (any orientation has outdeg <= Δ).
        for k in range(1, graph.max_degree + 2):
            cert = certificate(graph, [k] * graph.n)
            if cert is not None:
                return cert
        return None

    if len(f) != graph.n:
        raise ValueError(f"f length {len(f)} != n={graph.n}")
    max_out = [fi - 1 for fi in f]
    if any(mo < 0 for mo in max_out):
        return None

    for arcs, outdeg in _enumerate_orientations(graph, max_out):
        cert = _check_orientation(graph, arcs, outdeg)
        if cert is not None:
            return cert
    return None


def alon_tarsi_number(graph: Graph) -> int:
    """Minimum k such that G has an AT-good orientation with max outdeg = k-1."""
    if graph.n == 0:
        return 1
    # Lower bound: 1 for edgeless; else >= 2. Upper: Δ+1.
    lo = 1 if not graph.edges else 2
    for k in range(lo, graph.max_degree + 2):
        if certificate(graph, [k] * graph.n) is not None:
            return k
    return graph.max_degree + 1


def verify_certificate(graph: Graph, cert: ATCertificate) -> bool:
    """Independently re-check: arcs orient G, coeff ≠ 0, and even ≠ odd."""
    if not isinstance(cert, ATCertificate):
        return False
    if not _is_orientation_of(graph, cert.arcs):
        return False
    outdeg = _out_degrees(cert.arcs, graph.n)
    coeff = graph_polynomial_coefficient(graph, outdeg)
    even, odd = count_eulerian_subgraphs(cert.arcs, graph.n)
    if coeff == 0 or even == odd:
        return False
    return (
        cert.coefficient == coeff and cert.even == even and cert.odd == odd
    )
