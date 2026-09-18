# CranstonLafayetteRabern_P5GemFreeBK

## Informal statement
Every (P₅, gem)-free graph G with Δ(G) ≥ 9 satisfies χ(G) ≤ max{ω(G), Δ(G)−1}.
Here gem = K₁ ∨ P₄ (a vertex completely joined to a path on four vertices).
Equivalently: BK holds for graphs with no induced P₅ and no induced gem.

## Source
D. W. Cranston, H. Lafayette, L. Rabern, Coloring (P₅, gem)-free graphs with
Δ−1 colors, J. Graph Theory 101 (2022) 633–642; arXiv:2006.02015.

## Provenance
Agent-drafted stated target from the published abstract (JGT 2022 /
arXiv:2006.02015). Proofs deferred. This is a Rabern-authored worked reduction
to imitate; it is not a class-zoo endpoint for the hunt to target.

## Fidelity review
- P₅ is the path on five vertices (`0—1—2—3—4`), not P₄.
- Gem is K₁ ∨ P₄ with apex `0` and path `1—2—3—4`, matching the paper's
  `K₁ ∨ P₄`.
- Forbidden means *induced*: `G.induce s ≃g` the named graph, not a
  (non-induced) subgraph copy.
- The colouring bound is ordinary BK: `Colorable (max (maxDegree - 1) cliqueNum)`
  under `9 ≤ maxDegree`.
- Other forbidden-subgraph BK results (odd-hole-free, P₆-free, …) are not this
  theorem and are not ingested.

## Sanity checks
Concrete Adj + K₁₀ numeric probes live in
[`SanityChecks.lean`](SanityChecks.lean) (`decide` only; independent of any
`sorry` proof). See `docs/TRUST.md`.
