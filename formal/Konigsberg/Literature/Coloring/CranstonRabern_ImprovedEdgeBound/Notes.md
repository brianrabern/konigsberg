# CranstonRabern_ImprovedEdgeBound

## Informal statement
Edge lower bounds for k-AT-critical graphs (MainCor k≥7; MinorCor k∈{5,6}) with cleared-denominator form.

## Source
Cranston–Rabern, arXiv:1602.02589 / ImprovedEdgeBound TeX (public domain).

## Provenance
Agent-drafted stated targets; `IsKATCritical` is an intentional empty stub pending AT in Areas.

## Fidelity review
(See statement comments; backfilled under FIDELITY_GATES.)

## Sanity checks
Concrete non-vacuity + conclusion probes live in [`SanityChecks.lean`](SanityChecks.lean)
(`decide` / `norm_num` only; independent of any `sorry` proof). See `docs/TRUST.md`.
