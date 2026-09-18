# CranstonRabern_ClawFreeBK

## Informal statement
Every claw-free graph G with Δ(G) ≥ 9 satisfies χ(G) ≤ max{ω(G), Δ(G)−1}.
Equivalently: every claw-free graph with χ ≥ Δ ≥ 9 contains a K_Δ.

## Source
D. W. Cranston, L. Rabern, Coloring claw-free graphs with Δ−1 colors,
SIAM J. Discrete Math. 27 (2013) 534–549; arXiv:1206.1269.

## Provenance
Agent-drafted stated target from the published theorem (SIDMA 2013 / arXiv
abstract). Proofs deferred. The join/reducibility engine of the paper is not
re-encoded here; see `CranstonRabern_BKEquivalentConjectures` and the
reducible-configuration seeds.

## Fidelity review
- Claw-free is “no induced K_{1,3}”: three pairwise-nonadjacent neighbours of
  one vertex. That is the standard induced-claw condition, not “no K_{1,3}
  subgraph” (every graph of maximum degree ≥ 3 has a K_{1,3} subgraph).
- Main theorem matches ordinary BK restricted to claw-free graphs:
  `Colorable (max (maxDegree - 1) cliqueNum)` under `9 ≤ maxDegree`.
- The equivalent clique form is `¬ Colorable (Δ−1)` ⇒ `ω ≥ Δ`.
- List-colouring claw-free BK (SIDMA 2017, Δ ≥ 69) is a different theorem
  (`CranstonRabern_ListClawFreeBK` in REFERENCES.toml) and is not this entry.

## Sanity checks
Concrete non-vacuity + conclusion probes live in
[`SanityChecks.lean`](SanityChecks.lean) (`decide` / `completeGraph_clawFree`
only; independent of any `sorry` proof). See `docs/TRUST.md`.
