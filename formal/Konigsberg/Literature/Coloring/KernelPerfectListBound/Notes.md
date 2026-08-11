# KernelPerfectListBound

## Informal statement
On a kernel-perfect orientation, |L(v)| > d⁺(v) for all v ⇒ G is L-colorable.

## Source
`\\label{KernelPerfectListBound}` in *Basic Graph Coloring*.

## Provenance
Agent-drafted stated target; human fidelity read.

## Fidelity review
Uses `Orientation.KernelPerfect` and `outDegree` from WP0 Kernel.lean; conclusion
is `ListColorable` (same as SecondListBound). Strict inequality `|L| > d⁺` matches
the book (not ≥). Quantifiers: all vertices, fixed orientation.

## Sanity checks
Concrete non-vacuity + conclusion probes live in [`SanityChecks.lean`](SanityChecks.lean)
(`decide` / `norm_num` only; independent of any `sorry` proof). See `docs/TRUST.md`.
