/-
Sanity checks for BorodinKostochka on K₁₀
(Δ = 9, ω = 10, max{Δ−1, ω} = 10). Independent of the `sorry`.
-/
import Konigsberg.Literature.Coloring.BorodinKostochka.Statements
import Konigsberg.Literature.SanityLib

namespace Konigsberg.Literature.Coloring.BorodinKostochka

open SimpleGraph Konigsberg.Literature.SanityLib

private abbrev G₁₀ := completeGraph (Fin 10)

example : 9 ≤ G₁₀.maxDegree := by
  have hΔ : G₁₀.maxDegree = 9 := by decide
  simp [hΔ]

example : max (G₁₀.maxDegree - 1) G₁₀.cliqueNum = 10 := by
  have hΔ : G₁₀.maxDegree = 9 := by decide
  have hω : G₁₀.cliqueNum = 10 := cliqueNum_completeGraph_fin 10
  simp [hΔ, hω]

end Konigsberg.Literature.Coloring.BorodinKostochka
