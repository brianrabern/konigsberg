# BasicIrreducible

## Book
`\label{BasicIrreducible}` — *Basic Graph Coloring*, §Coloring with prescribed list sizes.

> If G is f-irreducible, then f(v) ≤ d_G(v) for all v. In particular, 2|E| ≥ f(V).

## Fidelity review
Statement matches the book lemma (pointwise degree bound + handshake). Lean names
wrap the green Areas theorems `basicIrreducible` and `sum_le_two_mul_card_edgeFinset`
without weakening. Status `formalized` (not `stated`).

## Machinery
`Areas/Coloring/Irreducible.lean` (`FIrreducible`, `FChoosableZ`, `fH`).
