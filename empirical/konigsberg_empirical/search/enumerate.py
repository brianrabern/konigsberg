"""Graph enumeration via nauty/geng, with a built-in fallback for small n.

`geng` streams non-isomorphic graphs in graph6; we parse them into core.Graph.
When `geng` is not on PATH we fall back to networkx's Graph Atlas, which covers
all graphs up to 7 vertices — enough for most counterexample searches and for
CI, without a system dependency. Beyond n=7 without geng we raise, loudly, rather
than silently enumerate a subset.

Constraint semantics are enforced in Python (`_matches`) for BOTH backends, so
results are identical regardless of which one ran; geng additionally gets the
cheap, unambiguous flags (`-c`, edge bounds) as a generation-time optimization.
Supported constraints: connected(bool), min_degree, max_degree, min_edges,
max_edges.
"""
from __future__ import annotations

import shutil
import subprocess
from collections.abc import Iterator

from ..core import Graph

# Debian ships nauty's binaries under a `nauty-` prefix; upstream builds don't.
_GENG_CANDIDATES = ("geng", "nauty-geng")

# networkx's atlas covers 0..7 vertices exactly.
_ATLAS_MAX = 7


def _find_geng() -> str | None:
    for name in _GENG_CANDIDATES:
        path = shutil.which(name)
        if path:
            return path
    return None


def parse_graph6(text: str) -> Graph:
    """Parse a single graph6 string into a core.Graph.

    Implements the McKay graph6 format: a byte holds 6 data bits (char value
    minus 63); n is the first byte for n<=62, with 126-prefixed extended forms
    above that; the remaining bits are the upper triangle, column-major
    (0,1),(0,2),(1,2),(0,3),...
    """
    s = text.strip()
    if not s:
        raise ValueError("empty graph6 string")
    data = [ord(c) - 63 for c in s]
    if data[0] != 63:  # 63 (char '~') marks an extended n encoding
        n, idx = data[0], 1
    elif data[1] != 63:
        n = (data[1] << 12) + (data[2] << 6) + data[3]
        idx = 4
    else:
        n = sum(data[2 + k] << (30 - 6 * k) for k in range(6))
        idx = 8

    bits: list[int] = []
    for byte in data[idx:]:
        bits.extend((byte >> shift) & 1 for shift in (5, 4, 3, 2, 1, 0))

    edges: list[tuple[int, int]] = []
    k = 0
    for j in range(1, n):
        for i in range(j):
            if k < len(bits) and bits[k]:
                edges.append((i, j))
            k += 1
    return Graph.of(n, edges)


def _is_connected(g: Graph) -> bool:
    if g.n <= 1:
        return True
    seen = {0}
    stack = [0]
    while stack:
        v = stack.pop()
        for w in g.neighbors(v):
            if w not in seen:
                seen.add(w)
                stack.append(w)
    return len(seen) == g.n


def _matches(g: Graph, c: dict) -> bool:
    if not c:
        return True
    if c.get("connected") and not _is_connected(g):
        return False
    mind, maxd = c.get("min_degree"), c.get("max_degree")
    if mind is not None or maxd is not None:
        degs = [g.degree(v) for v in range(g.n)]
        if mind is not None and (not degs or min(degs) < mind):
            return False
        if maxd is not None and degs and max(degs) > maxd:
            return False
    m = len(g.edges)
    if c.get("min_edges") is not None and m < c["min_edges"]:
        return False
    return not (c.get("max_edges") is not None and m > c["max_edges"])


def _geng_graphs(geng: str, n: int, c: dict) -> Iterator[Graph]:
    cmd = [geng, "-q"]
    if c.get("connected"):
        cmd.append("-c")
    cmd.append(str(n))
    lo, hi = c.get("min_edges"), c.get("max_edges")
    if lo is not None or hi is not None:
        lo = 0 if lo is None else lo
        hi = n * (n - 1) // 2 if hi is None else hi
        cmd.append(f"{lo}:{hi}")

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            g = parse_graph6(line)
            if _matches(g, c):
                yield g
    finally:
        if proc.stdout is not None:
            proc.stdout.close()
        proc.wait()


def _atlas_graphs(n: int, c: dict) -> Iterator[Graph]:
    import networkx as nx

    for G in nx.graph_atlas_g():
        if G.number_of_nodes() != n:
            continue
        nodes = sorted(G.nodes())
        relabel = {v: i for i, v in enumerate(nodes)}
        g = Graph.of(n, [(relabel[u], relabel[v]) for u, v in G.edges()])
        if _matches(g, c):
            yield g


def all_graphs(n: int, *, constraints: dict | None = None) -> Iterator[Graph]:
    """Yield the non-isomorphic simple graphs on n vertices matching constraints.

    Uses geng if available (any n); otherwise the networkx atlas for n<=7. Raises
    for larger n when geng is absent rather than returning a partial answer.
    """
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n}")
    c = constraints or {}
    geng = _find_geng()
    if geng is not None:
        yield from _geng_graphs(geng, n, c)
    elif n <= _ATLAS_MAX:
        yield from _atlas_graphs(n, c)
    else:
        raise RuntimeError(
            f"enumeration for n={n} needs nauty's geng on PATH (install nauty); "
            f"the built-in atlas fallback only covers n<={_ATLAS_MAX}."
        )
