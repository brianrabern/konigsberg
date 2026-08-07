# TransitiveClusteringBigCliques

## Book
`gct.tex` `\label{TransitiveClusteringBigCliques}`: Let G be a connected
vertex-transitive graph and 𝒬 the collection of *all* maximum cliques. If
ω(G) ≥ (2/3)(Δ(G)+1), then either
- X_𝒬 is edgeless; or
- X_𝒬 is a cycle and G is the graph obtained from X_𝒬 by blowing up each
  vertex to a K_{ω/2}.

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
