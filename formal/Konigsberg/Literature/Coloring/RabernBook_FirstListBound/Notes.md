# RabernBook_FirstListBound

## Informal statement
If |L(v)| ≥ deg(v)+1 for all v, then G is L-colorable (pointwise (d+1)-choosable).

## Source
Rabern, *Basic Graph Coloring*, §Coloring with prescribed list sizes.

## Provenance
Hand-proved in Statements.lean (greedy induction). Status `formalized`.

## Fidelity review
(See statement comments; backfilled under FIDELITY_GATES.)

## Sanity checks
Concrete non-vacuity + conclusion probes live in [`SanityChecks.lean`](SanityChecks.lean)
(`decide` / `norm_num` only; independent of any `sorry` proof). See `docs/TRUST.md`.
