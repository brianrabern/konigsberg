# CranstonRabern_BrooksAndBeyond

## Informal statement
Every graph satisfies χ ≤ max{3, ω, Δ} (preferred Brooks form in the
survey). The same bound holds for χ_ℓ (Theorem 8.3). If Δ ≥ 3 and G
contains no K_{Δ+1}, then α ≥ n/Δ (Lemma 8.1).

## Source
D. W. Cranston, L. Rabern, Brooks' Theorem and Beyond,
J. Graph Theory 80 (2015) 199–225; arXiv:1403.0479.

## Provenance
Agent-drafted stated targets from the published preferred formulation,
Theorem 8.3, and Lemma 8.1. The paper is a survey of *proofs*; these
three are the load-bearing numbered bounds. Theorem 9.1 (connected ⇔
degree-choosable iff not a Gallai tree) is already `BrooksListForm`.

## Fidelity review
- `max 3 (max cliqueNum maxDegree)` is max{3, ω, Δ}.
- `brooks_max3` is classical Brooks, not original to this paper; it is
  the formulation they work with. EXTERNAL `BrooksLean` is the equivalent
  ¬Δ-colorable ⇒ K_{Δ+1} or odd-cycle form under a different pin.
- `list_brooks_max3` is journal Theorem 8.3 / arXiv Theorem 10, proved
  via the Kernel Lemma and the independence lemma.
- Journal Lemma 8.1 / arXiv Lemma 8: α ≥ |G|/Δ if G contains no K_{Δ+1}.
  As written on arXiv that is false for odd cycles (C₅: Δ = 2, α = 2 < 5/2).
  The journal statement includes Δ > 2; we encode `3 ≤ maxDegree`.
  Division by Δ is then well-defined. `ω ≤ Δ` is “no K_{Δ+1}”.
- Degree-choosable ⇔ not a Gallai tree is journal Theorem 9.1 / arXiv
  Theorem 11, already `BrooksListForm`. Degree-paintable analogue is
  discussed but not encoded (no paintability predicate in `Areas/Coloring`).
- The eight chromatic proofs, Catlin's strengthening, Borodin's
  variable-degeneracy, and complexity remarks are not encoded. Pin them
  from the paper before stating them in Lean.
- BK and Reed appear only as concluding conjectures; they are already
  `BorodinKostochka` / `ReedConjecture` in REFERENCES.toml.

## Sanity checks
Concrete probes on K₄ / K₁ live in [`SanityChecks.lean`](SanityChecks.lean)
(`decide` / `cliqueNum_completeGraph_fin` only; independent of any `sorry`
proof). See `docs/TRUST.md`.
