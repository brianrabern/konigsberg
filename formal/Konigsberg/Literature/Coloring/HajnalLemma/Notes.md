# HajnalLemma

## Informal statement
For a nonempty collection 𝒬 of maximum cliques, |⋃𝒬| + |⋂𝒬| ≥ 2ω(G).

## Source
`\\label{HajnalLemma}` (gct 551–553).

## Provenance
Agent-drafted stated target; human fidelity read caught missing Nonempty (empty ⋂ = univ). SanityChecks lock that fix.

## Fidelity review
- Members of 𝒬 are maximum cliques via `𝒬 ⊆ maxCliqueCollection G` (book: “a
  collection of maximum cliques” — arbitrary subcollections, not only the full
  collection; Kostochka’s proof applies Hajnal to proper subcollections).
- **`𝒬.Nonempty` is required.** Empty `𝒬` makes `⋂ Q ∈ ∅ = univ` in Lean, so
  the claim becomes `0 + |V| ≥ 2ω`, false for `K_n`. The book’s usage (and the
  Kostochka proof’s `r ≥ 3`) assumes a nonempty collection.
- Cardinalities via `Set.ncard` on union/intersection; RHS `2 * cliqueNum`.

## Sanity checks
Concrete non-vacuity + conclusion probes live in [`SanityChecks.lean`](SanityChecks.lean)
(`decide` / `norm_num` only; independent of any `sorry` proof). See `docs/TRUST.md`.
