# Rabern_4ListCriticalEdgeBound

## Informal statement
Non-complete k-list-critical graphs have d(G) ≥ k−1+(k−3)/(k²−2k+2); Kernel Magic bound with mic(G).

## Source
Rabern, Elec. J. Combin. 2016 / 4ListCriticalEdgeBound TeX (public domain).

## Provenance
Agent-drafted stated targets; human fidelity read.

## Fidelity review
(See statement comments; backfilled under FIDELITY_GATES.)

## Sanity checks
Concrete non-vacuity + conclusion probes live in [`SanityChecks.lean`](SanityChecks.lean)
(`decide` / `norm_num` only; independent of any `sorry` proof). See `docs/TRUST.md`.
