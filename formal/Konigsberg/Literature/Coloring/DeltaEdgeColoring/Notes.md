# DeltaEdgeColoring

## Informal statement
Every bipartite graph is Δ-edge-colorable (line graph is Δ-colorable).

## Source
`\\label{DeltaEdgeColoring}` in *Basic Graph Coloring*.

## Provenance
Agent-drafted stated target; human fidelity read.

## Fidelity review
Stated via `lineGraph.Colorable maxDegree` (edge coloring = vertex coloring of
the line graph). Hypothesis `IsBipartite` (= `Colorable 2`). Toward BK for
line graphs.

## Sanity checks
Concrete non-vacuity + conclusion probes live in [`SanityChecks.lean`](SanityChecks.lean)
(`decide` / `norm_num` only; independent of any `sorry` proof). See `docs/TRUST.md`.
