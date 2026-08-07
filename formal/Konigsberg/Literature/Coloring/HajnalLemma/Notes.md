# HajnalLemma

## Book
`\label{HajnalLemma}` (gct 551–553): If G is a graph and 𝒬 is a collection of
maximum cliques in G, then |⋃𝒬| + |⋂𝒬| ≥ 2ω(G).

## Fidelity review
- Members of 𝒬 are maximum cliques via `𝒬 ⊆ maxCliqueCollection G` (book: “a
  collection of maximum cliques” — arbitrary subcollections, not only the full
  collection; Kostochka’s proof applies Hajnal to proper subcollections).
- **`𝒬.Nonempty` is required.** Empty `𝒬` makes `⋂ Q ∈ ∅ = univ` in Lean, so
  the claim becomes `0 + |V| ≥ 2ω`, false for `K_n`. The book’s usage (and the
  Kostochka proof’s `r ≥ 3`) assumes a nonempty collection.
- Cardinalities via `Set.ncard` on union/intersection; RHS `2 * cliqueNum`.
