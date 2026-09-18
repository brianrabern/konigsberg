/-
Sanity checks for CranstonRabern_ClawFreeBK.
Does not invoke the `sorry` theorems.
-/
import Konigsberg.Literature.Coloring.CranstonRabern_ClawFreeBK.Statements
import Konigsberg.Literature.SanityLib

namespace Konigsberg.Literature.Coloring.CranstonRabern_ClawFreeBK

open SimpleGraph Konigsberg.Literature.SanityLib

private abbrev G₄ := completeGraph (Fin 4)
private abbrev G₁₀ := completeGraph (Fin 10)

/-- Non-vacuity: K₄ is claw-free (the `ClawFree` hypothesis is inhabitable). -/
example : ClawFree G₄ := completeGraph_clawFree 4

/-- Conclusion probe on K₁₀ (Δ = 9, ω = 10) without invoking the theorem. -/
example : 9 ≤ G₁₀.maxDegree := by
  have hΔ : G₁₀.maxDegree = 9 := by decide
  simp [hΔ]

example : max (G₁₀.maxDegree - 1) G₁₀.cliqueNum = 10 := by
  have hΔ : G₁₀.maxDegree = 9 := by decide
  have hω : G₁₀.cliqueNum = 10 := cliqueNum_completeGraph_fin 10
  simp [hΔ, hω]

end Konigsberg.Literature.Coloring.CranstonRabern_ClawFreeBK
