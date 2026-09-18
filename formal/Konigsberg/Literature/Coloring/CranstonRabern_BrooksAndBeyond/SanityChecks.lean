/-
Sanity checks for CranstonRabern_BrooksAndBeyond on K₄ / K₁.
Does not invoke the `sorry` theorems.
-/
import Konigsberg.Literature.Coloring.CranstonRabern_BrooksAndBeyond.Statements
import Konigsberg.Literature.SanityLib

namespace Konigsberg.Literature.Coloring.CranstonRabern_BrooksAndBeyond

open Finset SimpleGraph Konigsberg.Areas.Coloring Konigsberg.Literature.SanityLib

private abbrev G₄ := completeGraph (Fin 4)
private abbrev G₁ := completeGraph (Fin 1)

/-- On K₄: max{3, ω, Δ} = max{3, 4, 3} = 4. -/
example : max 3 (max G₄.cliqueNum G₄.maxDegree) = 4 := by
  have hω : G₄.cliqueNum = 4 := cliqueNum_completeGraph_fin 4
  have hΔ : G₄.maxDegree = 3 := by decide
  simp [hω, hΔ]

/-- On K₁: max{3, ω, Δ} = 3; K₁ is 1-choosable. -/
example : max 3 (max G₁.cliqueNum G₁.maxDegree) = 3 := by
  have hω : G₁.cliqueNum = 1 := cliqueNum_completeGraph_fin 1
  have hΔ : G₁.maxDegree = 0 := by decide
  simp [hω, hΔ]

example : Choosable G₁ (Fintype.card (Fin 1)) := choosable_card G₁

/-- Lemma 8.1's numeric packing on K₄ is false (ω = Δ+1), so the hypothesis
`ω ≤ Δ` fails — we only check that packing on an edgeless pair (Δ = 0 is
out of range; use 2K₂? Skip). Singleton independent set in K₄ has size 1. -/
example : G₄.IsIndepSet ({(0 : Fin 4)} : Set (Fin 4)) := by
  intro a ha b hb
  simp at ha hb
  subst ha
  subst hb
  simp

end Konigsberg.Literature.Coloring.CranstonRabern_BrooksAndBeyond
