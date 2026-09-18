/-
Sanity checks for CranstonRabern_ChiEqDeltaBigCliques on K₁₆
(χ = Δ+1 ≥ Δ, Δ = 15 ≥ 13, ω = 16 ≥ Δ−3). Independent of the `sorry`s.
-/
import Konigsberg.Literature.Coloring.CranstonRabern_ChiEqDeltaBigCliques.Statements
import Konigsberg.Literature.SanityLib

namespace Konigsberg.Literature.Coloring.CranstonRabern_ChiEqDeltaBigCliques

open SimpleGraph Konigsberg.Literature.SanityLib

private abbrev G₁₆ := completeGraph (Fin 16)

example : 13 ≤ G₁₆.maxDegree := by
  have hΔ : G₁₆.maxDegree = 15 := by decide
  simp [hΔ]

example : G₁₆.maxDegree - 3 ≤ G₁₆.cliqueNum := by
  have hΔ : G₁₆.maxDegree = 15 := by decide
  have hω : G₁₆.cliqueNum = 16 := cliqueNum_completeGraph_fin 16
  simp [hΔ, hω]

example : G₁₆.maxDegree ≤ G₁₆.cliqueNum := by
  have hΔ : G₁₆.maxDegree = 15 := by decide
  have hω : G₁₆.cliqueNum = 16 := cliqueNum_completeGraph_fin 16
  simp [hΔ, hω]

end Konigsberg.Literature.Coloring.CranstonRabern_ChiEqDeltaBigCliques
