# CranstonRabern_ChiEqDeltaBigCliques

## Informal statement
If Δ ≥ 13 and χ ≥ Δ, then ω ≥ Δ−3. If χ ≥ Δ, then either ω ≥ Δ or the
subgraph induced by degree-Δ vertices has clique number at least Δ−5.

## Source
D. W. Cranston, L. Rabern, Graphs with χ = Δ have big cliques,
SIAM J. Discrete Math. 29 (2015) 1792–1814; arXiv:1305.3526.

## Provenance
Agent-drafted stated targets from the published abstract (journal form:
Δ ≥ 13 and χ ≥ Δ ⇒ ω ≥ Δ−3; and χ ≥ Δ ⇒ ω ≥ Δ or ω(H) ≥ Δ−5).

## Fidelity review
- `χ ≥ Δ` is `¬ Colorable (maxDegree − 1)`, which is exact (Colorable k ↔ χ ≤ k).
- The arXiv v1 phrasing “Δ ≥ 13 and ω ≤ Δ−4 ⇒ χ ≤ Δ−1” is the contrapositive
  of the main theorem; we state the journal χ ≥ Δ form.
- High-vertex subgraph is `G.induce {v | deg v = Δ}`.
- Δ = 9 (the live BK regime) is *not* covered; this is a Δ ≥ 13 result.
- The paper's Δ = 13 ⇒ K₁₀ lemma is not encoded separately.

## Sanity checks
Concrete probes on K₁₆ live in [`SanityChecks.lean`](SanityChecks.lean)
(`decide` / `cliqueNum_completeGraph_fin` only; independent of any `sorry`
proof). See `docs/TRUST.md`.
