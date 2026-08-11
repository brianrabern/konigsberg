# KostochkaYanceyKernelLemma

## Informal statement
Superorientation with independent I and back-arrows on G−I ⇒ kernel-perfect.

## Source
`\\label{KostochkaYanceyKernelLemma}` in *Basic Graph Coloring*.

## Provenance
Agent-drafted stated target; human fidelity read.

## Fidelity review
`HasBackArrows` on `univ \ I` encodes “all edges in G−I have back arrows”
(bidirected). Conclusion is `Superorientation.KernelPerfect`.

## Sanity checks
Concrete non-vacuity + conclusion probes live in [`SanityChecks.lean`](SanityChecks.lean)
(`decide` / `norm_num` only; independent of any `sorry` proof). See `docs/TRUST.md`.
