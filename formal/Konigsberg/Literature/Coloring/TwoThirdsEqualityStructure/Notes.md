# TwoThirdsEqualityStructure

## Informal statement
ω ≥ (2/3)(Δ+1) and X_𝒬 connected ⇒ ⋂𝒬 ≠ ∅, or Δ(X)≤2 with the half-ω intersection geometry.

## Source
`\\label{TwoThirdsEqualityStructure}` (gct 571–578).

## Provenance
Agent-drafted stated target; human fidelity read vs gct (half-ω as 2·|A∩B|=ω).

## Fidelity review
(line-by-line)
| Book | Lean |
|---|---|
| 𝒬 a collection of maximum cliques | `𝒬 ⊆ maxCliqueCollection G` (arbitrary subcollection OK) |
| ω ≥ (2/3)(Δ+1) | `3 * cliqueNum ≥ 2 * maxDegree + 2` |
| X_𝒬 connected | `(cliqueIntersectionGraph 𝒬).Connected` |
| ∩𝒬 ≠ ∅ | `(⋂ Q ∈ 𝒬, (Q : Set V)).Nonempty` |
| Δ(X_𝒬) ≤ 2 | three neighbours of Q force a coincidence |
| B, C distinct neighbours of A | `X.Adj A B`, `X.Adj A C`, `B ≠ C` |
| B ∩ C = ∅ | Finset intersection empty |
| \|A∩B\| = \|A∩C\| = ½ω | `2 * #(A ∩ B) = cliqueNum` (and same for C) — avoids ℕ `/` floor |

Verified against gct 571–578. Medium→high confidence after this read.

## Sanity checks
Concrete non-vacuity + conclusion probes live in [`SanityChecks.lean`](SanityChecks.lean)
(`decide` / `norm_num` only; independent of any `sorry` proof). See `docs/TRUST.md`.
