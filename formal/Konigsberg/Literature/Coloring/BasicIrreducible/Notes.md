# BasicIrreducible

## Informal statement
If G is f-irreducible, then f(v) ≤ d(v) for all v; in particular ∑ f ≤ 2|E|.

## Source
`\\label{BasicIrreducible}` — Rabern, *Basic Graph Coloring*, §Coloring with prescribed list sizes.

## Provenance
Lean statement wraps green Areas theorems; selected and fidelity-read by hand. Status `formalized`.

## Fidelity review
Statement matches the book lemma (pointwise degree bound + handshake). Lean names
wrap the green Areas theorems `basicIrreducible` and `sum_le_two_mul_card_edgeFinset`
without weakening. Status `formalized` (not `stated`).

## Sanity checks
Concrete non-vacuity + conclusion probes live in [`SanityChecks.lean`](SanityChecks.lean)
(`decide` / `norm_num` only; independent of any `sorry` proof). See `docs/TRUST.md`.
