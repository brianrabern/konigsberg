# EulerianOrientationsLemma

## Informal statement
For an orientation o, |EE−EO| = |p_{d⁺}(G)| (absolute values).

## Source
Book env `EulerianOrientationsLemma`.

## Provenance
Agent-drafted stated target matching the empirical AT certificate shape; human fidelity read.

## Fidelity review
Stated as equality of absolute values between `eulerianSignDiff` and
`graphPolynomialCoeff` at the out-degree monomial — the form used by the
empirical AT verifier.

## Sanity checks
Concrete non-vacuity + conclusion probes live in [`SanityChecks.lean`](SanityChecks.lean)
(`decide` / `norm_num` only; independent of any `sorry` proof). See `docs/TRUST.md`.
