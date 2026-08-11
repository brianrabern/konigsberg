# KostochkaCliqueGraph

## Informal statement
If 𝒬 ⊆ max cliques, ω > (2/3)(Δ+1), and X_𝒬 connected, then ⋂𝒬 ≠ ∅.

## Source
`\\label{KostochkaCliqueGraph}` in gct / *Basic Graph Coloring*.

## Provenance
Agent-drafted stated target; human fidelity read.

## Fidelity review
Strict inequality ω > (2/3)(Δ+1) encoded as `2(Δ+1) < 3ω` in ℕ.
`cliqueIntersectionGraph 𝒬` is X_𝒬; conclusion is nonempty intersection of
the cliques as sets.

## Sanity checks
Concrete non-vacuity + conclusion probes live in [`SanityChecks.lean`](SanityChecks.lean)
(`decide` / `norm_num` only; independent of any `sorry` proof). See `docs/TRUST.md`.
