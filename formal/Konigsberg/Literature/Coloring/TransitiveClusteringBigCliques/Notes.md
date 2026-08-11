# TransitiveClusteringBigCliques

## Informal statement
Connected vertex-transitive G with ω ≥ (2/3)(Δ+1): X_𝒬 edgeless, or X_𝒬≃C_n and G≃cliqueBlowup C_n (ω/2).

## Source
`\\label{TransitiveClusteringBigCliques}` (gct).

## Provenance
Agent-drafted stated target; human fidelity read restored the blow-up conclusion (not only the cycle condition).

## Fidelity review
- Uses the full `maxCliqueCollection` (not an arbitrary subcollection) — matches
  the book’s “the collection of all maximum cliques.”
- Edgeless alternative: `(cliqueIntersectionGraph 𝒬).edgeSet = ∅`.
- Blow-up alternative asserts **both** `X_𝒬 ≃ C_n` **and**
  `G ≃ cliqueBlowup C_n (ω/2)` via `Areas.Coloring.cliqueBlowup` (within-fibre
  cliques + complete bipartite joins along cycle edges). This is the book’s
  conclusion, not a necessary-condition shadow.
- `Even G.cliqueNum` so `ω/2` is integral (book’s ½ω).
- Non-strict ω inequality as `3ω ≥ 2(Δ+1)`.

## Sanity checks
Concrete non-vacuity + conclusion probes live in [`SanityChecks.lean`](SanityChecks.lean)
(`decide` / `norm_num` only; independent of any `sorry` proof). See `docs/TRUST.md`.
