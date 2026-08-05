"""Generate FixerBreaker differential corpus via the .NET oracle.

Requires a built oracle (`dotnet build vendor/choosability-oracle/... -c Release`)
and `dotnet` on PATH. Writes tests/differential/fixtures/fixer_breaker_corpus.jsonl.

Template rule (agreement, not a specific coloring question):
  sizes[v] = degree(v); two pots: max_pot = max(sizes) and max(sizes)+1.
  Skip edgeless graphs (max(sizes)==0).

Default: n <= 5 (committed corpus stays CI-friendly). Pass --max-n 6/7 to widen.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from konigsberg_empirical.core import Graph
from konigsberg_empirical.search.enumerate import all_graphs

ROOT = Path(__file__).resolve().parents[2]
ORACLE_PROJECT = ROOT / "vendor" / "choosability-oracle" / "oracle" / "Oracle.csproj"
OUT = Path(__file__).parent / "fixtures" / "fixer_breaker_corpus.jsonl"


def _to_graph6(graph: Graph) -> str:
    import networkx as nx

    G = nx.Graph()
    G.add_nodes_from(range(graph.n))
    G.add_edges_from(graph.edges)
    return nx.to_graph6_bytes(G, header=False).decode().strip()


def _cases_for_graph(graph: Graph) -> list[dict]:
    if not graph.edges:
        return []
    sizes = [graph.degree(v) for v in range(graph.n)]
    base = max(sizes)
    if base <= 0:
        return []
    edges = [list(e) for e in sorted(graph.edges)]
    out = []
    for max_pot in (base, base + 1):
        out.append(
            {
                "n": graph.n,
                "edges": edges,
                "sizes": sizes,
                "max_pot": max_pot,
                "graph6": _to_graph6(graph),
            }
        )
    return out


def _find_oracle_dll() -> Path | None:
    for cfg in ("Release", "Debug"):
        dll = (
            ROOT
            / "vendor"
            / "choosability-oracle"
            / "oracle"
            / "bin"
            / cfg
            / "net10.0"
            / "choosability-oracle.dll"
        )
        if dll.exists():
            return dll
        # also try net8.0
        dll = dll.parent.parent / "net8.0" / "choosability-oracle.dll"
        if dll.exists():
            return dll
    return None


def _start_oracle() -> subprocess.Popen:
    if not shutil.which("dotnet"):
        raise SystemExit("dotnet not on PATH; build/run the oracle on a machine with the SDK")
    dll = _find_oracle_dll()
    if dll is None:
        raise SystemExit(
            f"oracle dll not found; run: dotnet build {ORACLE_PROJECT} -c Release"
        )
    return subprocess.Popen(
        ["dotnet", str(dll)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(ROOT),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-n", type=int, default=5, help="enumerate graphs up to this n")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    # Hard gate: selftest must pass before any corpus is written.
    print("running oracle --selftest ...", flush=True)
    st = subprocess.run(
        ["dotnet", "run", "--project", str(ORACLE_PROJECT), "-c", "Release", "--no-build",
         "--", "--selftest"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if st.returncode != 0:
        # try with build
        st = subprocess.run(
            ["dotnet", "run", "--project", str(ORACLE_PROJECT), "-c", "Release",
             "--", "--selftest"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
    sys.stdout.write(st.stdout)
    sys.stderr.write(st.stderr)
    if st.returncode != 0:
        raise SystemExit("oracle --selftest failed; refusing to generate corpus")

    requests: list[dict] = []
    for n in range(1, args.max_n + 1):
        for g in all_graphs(n):
            requests.extend(_cases_for_graph(g))
    print(f"streaming {len(requests)} cases through oracle ...", flush=True)

    proc = _start_oracle()
    assert proc.stdin and proc.stdout
    records: list[dict] = []
    try:
        for i, req in enumerate(requests):
            line = json.dumps(
                {"n": req["n"], "edges": req["edges"], "sizes": req["sizes"],
                 "max_pot": req["max_pot"]}
            )
            proc.stdin.write(line + "\n")
            proc.stdin.flush()
            out = proc.stdout.readline()
            if not out:
                err = proc.stderr.read() if proc.stderr else ""
                raise SystemExit(f"oracle died on case {i}: {err}")
            resp = json.loads(out)
            records.append({**req, **resp})
            if (i + 1) % 50 == 0:
                print(f"  {i + 1}/{len(requests)}", flush=True)
    finally:
        proc.stdin.close()
        proc.wait(timeout=30)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w") as f:
        for rec in records:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
    print(f"wrote {len(records)} records → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
