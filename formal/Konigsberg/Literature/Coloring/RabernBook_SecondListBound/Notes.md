# RabernBook_SecondListBound

## Informal statement
If an acyclic orientation has |L(v)| ≥ d⁺(v)+1 for all v, then G is L-colorable.

## Source
Rabern, *Basic Graph Coloring*, §Coloring with prescribed list sizes.

## Provenance
Thin wrapper around Areas `fChoosable_outDegree_succ`. Status `formalized`.

## Fidelity review
(See statement comments; backfilled under FIDELITY_GATES.)

## Sanity checks
Concrete non-vacuity + conclusion probes live in [`SanityChecks.lean`](SanityChecks.lean)
(`decide` / `norm_num` only; independent of any `sorry` proof). See `docs/TRUST.md`.
