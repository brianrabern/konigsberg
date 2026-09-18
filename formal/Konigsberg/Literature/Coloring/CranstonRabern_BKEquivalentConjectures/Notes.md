# CranstonRabern_BKEquivalentConjectures

## Informal statement
Borodin–Kostochka is equivalent to: every graph with χ = Δ = 9 contains a
(not necessarily induced) copy of the join K₃ ∗ Ē₆. Separately: if a join
A ∗ B of two graphs on at least two vertices each is f-choosable for
f(v) = d(v)−1, then it is not an induced subgraph of a D-critical graph
with Δ = D.

## Source
D. W. Cranston, L. Rabern, Coloring a graph with Δ−1 colors: conjectures
equivalent to the Borodin–Kostochka conjecture that appear weaker,
European J. Combin. 44 (2015) 23–42; arXiv:1203.5380.

## Provenance
Agent-drafted stated targets from the published abstract / Conjecture 1.17
and the Section 4 join-exclusion engine. The full classified list of
f-choosable joins is not encoded.

## Fidelity review
- `graphJoin` is the ordinary join (disjoint union plus all cross edges).
- Subgraph copy of K₃ ∗ Ē₆ is a `SimpleGraph.Embedding` (`↪g`), not an
  induced embedding — matching “as a subgraph” in the equivalent conjecture.
- Induced exclusion of an f-choosable join uses `≃g` on `G.induce s`.
- `χ = Δ = 9` is encoded as `maxDegree = 9` and `¬ Colorable 8`.
- Ordinary BK is `Colorable (max cliqueNum (maxDegree − 1))` under Δ ≥ 9.
- Other equivalent weakenings (A₁ ∗ A₂ with |Aᵢ| ≥ 3, etc.) are omitted;
  pin them from the paper before stating them in Lean.

## Sanity checks
Concrete non-vacuity probes live in [`SanityChecks.lean`](SanityChecks.lean)
(`decide` only; independent of any `sorry` proof). See `docs/TRUST.md`.
