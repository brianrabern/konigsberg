# Rabern_HittingMaxCliques

## Informal statement
If ω(G) ≥ (3/4)(Δ(G)+1), then G has an independent set I meeting every
maximum clique — equivalently, ω(G−I) < ω(G).

## Source
L. Rabern, On hitting all maximum cliques with an independent set,
J. Graph Theory 66 (2011) 32–37; arXiv:0907.3705.

## Provenance
Agent-drafted stated target from the paper's main theorem (and the
existing REFERENCES.toml pin). Used to bound a minimum counterexample
to Reed's conjecture; relevant to Kostochka's reduction / transversal
half of the BK attack.

## Fidelity review
- Threshold is **3/4, not 2/3**. The 2/3 theory is `KostochkaCliqueGraph` /
  `TwoThirdsEqualityStructure` (clique-intersection structure), a different
  theorem. Do not conflate them.
- Encoded as `4ω ≥ 3(Δ+1)` in ℕ.
- Independent set is a `Finset`; `G−I` is `G.induce Iᶜ`.
- King (arXiv:0911.1741) improved the constant; that improvement is *not*
  this statement. The sharp constant remains open.
- C₅[K_r] sits at ω/(Δ+1) = 2/3 and fails the hitting property — below
  the 3/4 hypothesis, so not a counterexample to this theorem.

## Sanity checks
Concrete probes on K₃ live in [`SanityChecks.lean`](SanityChecks.lean)
(`decide` / `cliqueNum_completeGraph_fin` only; independent of any `sorry`
proof). See `docs/TRUST.md`.
