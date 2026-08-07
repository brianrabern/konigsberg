# TwoThirdsEqualityStructure

## Book
`gct.tex` `\label{TwoThirdsEqualityStructure}`: If 𝒬 is a collection of
maximum cliques in G with ω(G) ≥ (2/3)(Δ(G)+1) such that X_𝒬 is connected,
then either
- ∩𝒬 ≠ ∅; or
- Δ(X_𝒬) ≤ 2 and if B, C ∈ 𝒬 are different neighbours of A ∈ 𝒬, then
  B ∩ C = ∅ and |A ∩ B| = |A ∩ C| = ½ ω(G).

## Fidelity review (line-by-line)
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
