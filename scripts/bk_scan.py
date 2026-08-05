#!/usr/bin/env python3
"""Scan for k-choice-critical graphs carrying a bad K2 — the BK-attack search.

Enumerates connected graphs with degrees in {3,4} (via nauty's geng when
available, else the built-in atlas for n<=7), filters to those with a bad-K2 edge
/ no K4 / k-colorable, and reports the k-choice-critical ones. Composed on the
CEGAR choosability engine (konigsberg_empirical.coloring.bk).

CAVEATS (printed at run time), inherited from find_bad_list:
  * A reported bad list is CERTAIN and independently re-checkable.
  * With --palette below k*n, a "critical" verdict is strong evidence up to that
    palette, NOT a proof. Omit --palette for a complete (slower) decision.

Usage:  python scripts/bk_scan.py --nmin 6 --nmax 12 -k 3 --palette 7
"""
from __future__ import annotations

import argparse
import contextlib
import json
import sys
import time

from konigsberg_empirical.coloring.bk import find_bad_k2_critical
from konigsberg_empirical.core import Graph
from konigsberg_empirical.search.enumerate import all_graphs

_THREE_FOUR = {"connected": True, "min_degree": 3, "max_degree": 4}


def to_graph6(g: Graph) -> str:
    """graph6 string for a hit, for interop; falls back to an edge list."""
    try:
        import networkx as nx

        G = nx.Graph()
        G.add_nodes_from(range(g.n))
        G.add_edges_from(g.edges)
        return nx.to_graph6_bytes(G, header=False).decode().strip()
    except ImportError:
        return f"n={g.n} edges={sorted(g.edges)}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="scan for k-choice-critical bad-K2 graphs")
    ap.add_argument("--nmin", type=int, default=6)
    ap.add_argument("--nmax", type=int, default=12)
    ap.add_argument("-k", type=int, default=3, help="list size")
    ap.add_argument("--palette", type=int, default=None,
                    help="color bound; omit for a complete (slower) decision at k*n")
    ap.add_argument("--out", default=None, help="append hits here as JSONL")
    a = ap.parse_args(argv)

    print(f"# k={a.k} palette={a.palette or 'k*n (complete)'} n={a.nmin}..{a.nmax}", flush=True)
    print("# CAVEAT: a bad list is a certain, re-checkable witness.", flush=True)
    if a.palette is not None:
        print(f"# CAVEAT: 'critical' is evidence only up to palette {a.palette}, not proof.",
              flush=True)

    total = 0
    with (open(a.out, "a") if a.out else contextlib.nullcontext()) as out:
        for n in range(a.nmin, a.nmax + 1):
            t0 = time.time()
            hits = 0
            for hit in find_bad_k2_critical(all_graphs(n, constraints=_THREE_FOUR),
                                            k=a.k, palette=a.palette):
                total += 1
                hits += 1
                g6 = to_graph6(hit["graph"])
                rec = {
                    "n": n, "graph6": g6, "bad_k2_edges": hit["bad_k2_edges"],
                    "bad_list": hit["bad_list"], "critical": hit["critical"],
                }
                print(f"  !! HIT n={n} {g6} critical={hit['critical']} "
                      f"badK2={hit['bad_k2_edges']} L={hit['bad_list']}", flush=True)
                if out:
                    out.write(json.dumps(rec) + "\n")
                    out.flush()
            print(f"n={n}: {hits} hit(s)  [{time.time() - t0:.1f}s]", flush=True)

    print(f"# done: {total} hit(s)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
