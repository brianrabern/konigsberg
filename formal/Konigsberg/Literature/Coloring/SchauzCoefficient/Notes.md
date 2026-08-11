# SchauzCoefficient

## Informal statement
Coefficient formula: with |A_i|=k_i+1 and ∑k=deg f, f_k = ∑_{a∈∏A} f(a)/N(a).

## Source
Book §A coefficient formula (Combinatorial nullstellensatz chapter).

## Provenance
Agent-drafted stated target; human fidelity read.

## Fidelity review
Exact-size lists (`card = k_i+1`), not ≥. Denominator `N` matches the book.
Uses division in a field (book works over arbitrary fields; zero denominators
are excluded by distinctness of A_i elements in the product).

## Sanity checks
Concrete non-vacuity + conclusion probes live in [`SanityChecks.lean`](SanityChecks.lean)
(`decide` / `norm_num` only; independent of any `sorry` proof). See `docs/TRUST.md`.
