# EulerianOrientationsLemma

## Book
`EulerianOrientationsLemma`: for an orientation `G⃗`,
`||EE| − |EO|| = ||DE_{d⁺} − DO_{d⁺}||`, and hence
`|p_{d⁺}(G)| = ||EE| − |EO||`.

## Fidelity review
Stated as equality of absolute values between `eulerianSignDiff` and
`graphPolynomialCoeff` at the out-degree monomial — the form used by the
empirical AT verifier.

## Empirical bridge
`alon_tarsi.verify_certificate` checks `even − odd = coefficient`. A future
proof of this lemma lets an AT certificate witness a *formalized* theorem.
