# KernelPerfectSuperListBound

## Informal statement
Same list bound for kernel-perfect superorientations (digons allowed).

## Source
`\\label{KernelPerfectSuperListBound}` in *Basic Graph Coloring*.

## Provenance
Agent-drafted stated target; human fidelity read.

## Fidelity review
Matches book: same conclusion as KernelPerfectListBound, hypothesis on a
`Superorientation` that is `KernelPerfect`, with `|L(v)| > d⁺(v)`.

## Sanity checks
Concrete non-vacuity + conclusion probes live in [`SanityChecks.lean`](SanityChecks.lean)
(`decide` / `norm_num` only; independent of any `sorry` proof). See `docs/TRUST.md`.
