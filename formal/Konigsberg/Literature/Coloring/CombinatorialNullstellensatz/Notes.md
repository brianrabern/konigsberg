# CombinatorialNullstellensatz

## Book
Unlabeled lemma at the start of ch. Combinatorial nullstellensatz: coefficient
criterion for a nonzero evaluation on a grid.

## Fidelity review
Matches Alon's CN: `∑ k = deg f`, nonzero monomial coeff, `|A_i| ≥ k_i+1` ⇒
nonzero evaluation. Field `F` arbitrary (book: arbitrary field).

## Empirical bridge
Upstream of `alon_tarsi` / `graph_polynomial_coefficient`: a nonzero `p_k(G)`
plus CN yields a coloring. Proving this formalizes the certificate→colorability
implication.
