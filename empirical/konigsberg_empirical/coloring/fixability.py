"""Clean-room (L,P)-fixability for edge-coloring — independent of SuperSlimBoard.

Faithful to Cranston–Rabern arXiv 1507.05600 Def. of (L,P)-fixable:

  (1) G admits an edge-coloring ζ with ζ(xy) ∈ L(x) ∩ L(y); or
  (2) ∃ a,b ∈ P such that for every partition of S_{L,a,b} into parts of size
      ≤ 2, ∃ a subset of parts to swap a↔b on so the resulting L' is fixable.

Used to adjudicate the nearly-colorable MindTests discrepancy.
"""
from __future__ import annotations

from konigsberg_empirical.core import Graph


def edge_colorable(graph: Graph, lists: list[set[int]]) -> bool:
    """Proper edge-coloring with ζ(uv) ∈ lists[u] ∩ lists[v]."""
    edges = sorted(graph.edges)
    if not edges:
        return True
    options = [sorted(lists[u] & lists[v]) for u, v in edges]
    # Backtracking in edge order; conflict = shared endpoint + same color.
    color_on: dict[tuple[int, int], int] = {}

    def ok(ei: int, c: int) -> bool:
        u, v = edges[ei]
        for ej, (x, y) in enumerate(edges):
            if ej >= ei:
                break
            if c == color_on[edges[ej]] and (u in (x, y) or v in (x, y)):
                return False
        return True

    def rec(ei: int) -> bool:
        if ei >= len(edges):
            return True
        for c in options[ei]:
            if ok(ei, c):
                color_on[edges[ei]] = c
                if rec(ei + 1):
                    return True
                del color_on[edges[ei]]
        return False

    return rec(0)


def edge_colorable_without(graph: Graph, lists: list[set[int]], skip: tuple[int, int]) -> bool:
    g2 = Graph.of(graph.n, [e for e in graph.edges if e != skip and e != (skip[1], skip[0])])
    return edge_colorable(g2, lists)


def is_nearly_edge_colorable(graph: Graph, lists: list[set[int]]) -> bool:
    return any(edge_colorable_without(graph, lists, e) for e in graph.edges)


def _s_ab(lists: list[set[int]], a: int, b: int) -> list[int]:
    """Vertices with exactly one of {a,b}."""
    return [v for v, L in enumerate(lists) if (a in L) ^ (b in L)]


def _swap(lists: list[set[int]], a: int, b: int, vertices: list[int]) -> list[set[int]]:
    out = [set(L) for L in lists]
    for v in vertices:
        L = out[v]
        has_a, has_b = a in L, b in L
        if has_a and not has_b:
            L.remove(a)
            L.add(b)
        elif has_b and not has_a:
            L.remove(b)
            L.add(a)
    return out


def _partitions_size_at_most_two(items: list[int]) -> list[list[list[int]]]:
    """All partitions of `items` into parts of size 1 or 2 (order irrelevant)."""
    items = list(items)
    if not items:
        return [[]]
    if len(items) == 1:
        return [[[items[0]]]]
    first, rest = items[0], items[1:]
    out: list[list[list[int]]] = []
    # singleton part
    for p in _partitions_size_at_most_two(rest):
        out.append([[first]] + p)
    # pair first with each later element
    for i, partner in enumerate(rest):
        remaining = rest[:i] + rest[i + 1 :]
        for p in _partitions_size_at_most_two(remaining):
            out.append([[first, partner]] + p)
    # dedupe by frozenset-of-frozensets
    seen: set[frozenset[frozenset[int]]] = set()
    uniq: list[list[list[int]]] = []
    for p in out:
        key = frozenset(frozenset(part) for part in p)
        if key not in seen:
            seen.add(key)
            uniq.append(p)
    return uniq


def is_fixable(
    graph: Graph, lists: list[set[int]], pot: set[int] | None = None, *, _memo: dict | None = None
) -> bool:
    """(L, pot)-fixable per Cranston–Rabern."""
    if pot is None:
        pot = set().union(*lists) if lists else set()
    key = (tuple(frozenset(L) for L in lists), frozenset(pot))
    if _memo is None:
        _memo = {}
    if key in _memo:
        return _memo[key] is True  # False or "computing" → not yet known / cycle

    if edge_colorable(graph, lists):
        _memo[key] = True
        return True

    _memo[key] = "computing"
    colors = sorted(pot)
    for i, a in enumerate(colors):
        for b in colors[i + 1 :]:
            S = _s_ab(lists, a, b)
            if not S:
                continue
            partitions = _partitions_size_at_most_two(S)
            all_ok = True
            for partition in partitions:
                found = False
                t = len(partition)
                for mask in range(1 << t):
                    chosen: list[int] = []
                    for j in range(t):
                        if mask & (1 << j):
                            chosen.extend(partition[j])
                    if not chosen:
                        continue  # identity swap — no progress
                    L2 = _swap(lists, a, b, chosen)
                    if is_fixable(graph, L2, pot, _memo=_memo):
                        found = True
                        break
                if not found:
                    all_ok = False
                    break
            if all_ok:
                _memo[key] = True
                return True

    _memo[key] = False
    return False


def enumerate_list_assignments(sizes: list[int], pot_size: int) -> list[list[set[int]]]:
    """All assignments L with |L(v)|=sizes[v], L(v)⊆{0..pot_size-1}, up to color perm.

    Uses the same bit-assignment generator as the engine for board count parity,
    then converts traces to list-of-sets. (Enumeration faithfulness is already
    fingerprint-checked; conversion is the clean-room object.)
    """
    from konigsberg_empirical.coloring.bit_assignments import generate_assignments

    out: list[list[set[int]]] = []
    for trace in generate_assignments(sizes, pot_size):
        n = len(sizes)
        lists: list[set[int]] = [set() for _ in range(n)]
        for c, bits in enumerate(trace):
            v = 0
            bb = bits
            while bb:
                if bb & 1:
                    lists[v].add(c)
                bb >>= 1
                v += 1
                if v >= n:
                    break
        out.append(lists)
    return out
