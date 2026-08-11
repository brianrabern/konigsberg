# CombinatorialNullstellensatz

## Informal statement
Alon's combinatorial Nullstellensatz: nonzero multi-degree coefficient + large enough grids ⇒ nonzero evaluation.

## Source
Unlabeled lemma opening the Combinatorial nullstellensatz chapter in *Basic Graph Coloring*.

## Provenance
Agent-drafted stated target shaped for the AT / graph-polynomial bridge; human fidelity read.

## Fidelity review
Matches Alon's CN: `∑ k = deg f`, nonzero monomial coeff, `|A_i| ≥ k_i+1` ⇒
nonzero evaluation. Field `F` arbitrary (book: arbitrary field).

## Sanity checks
Concrete non-vacuity + conclusion probes live in [`SanityChecks.lean`](SanityChecks.lean)
(`decide` / `norm_num` only; independent of any `sorry` proof). See `docs/TRUST.md`.
