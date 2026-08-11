/-
Sanity checks for TransitiveClusteringBigCliques on K₁.
-/
import Konigsberg.Literature.Coloring.TransitiveClusteringBigCliques.Statements
import Konigsberg.Literature.SanityLib

namespace Konigsberg.Literature.Coloring.TransitiveClusteringBigCliques

open Finset SimpleGraph Konigsberg.Areas.Coloring Konigsberg.Literature.SanityLib

private abbrev G₁ := completeGraph (Fin 1)

example : G₁.Connected := Connected.of_subsingleton

example : IsVertexTransitive G₁ := by
  intro u v
  refine ⟨RelIso.refl _, Subsingleton.elim u v⟩

example : 3 * G₁.cliqueNum ≥ 2 * G₁.maxDegree + 2 := by
  have hω : G₁.cliqueNum = 1 := cliqueNum_completeGraph_fin 1
  have hΔ : G₁.maxDegree = 0 := by
    simp [maxDegree, degree]
  simp [hω, hΔ]

/-- Single max-clique ⇒ X_𝒬 has no edges. -/
example : ∀ (x y : ↑(maxCliqueCollection G₁)),
    ¬ (cliqueIntersectionGraph (maxCliqueCollection G₁)).Adj x y := by
  intro x y h
  exact h.1 (Subtype.ext <| by
    have hx : G₁.IsNClique G₁.cliqueNum x.val := x.property
    have hy : G₁.IsNClique G₁.cliqueNum y.val := y.property
    rw [cliqueNum_completeGraph_fin 1] at hx hy
    have hxU := eq_univ_of_card x.val (by simpa [card_univ, Fintype.card_fin] using hx.card_eq)
    have hyU := eq_univ_of_card y.val (by simpa [card_univ, Fintype.card_fin] using hy.card_eq)
    exact hxU.trans hyU.symm)

end Konigsberg.Literature.Coloring.TransitiveClusteringBigCliques
