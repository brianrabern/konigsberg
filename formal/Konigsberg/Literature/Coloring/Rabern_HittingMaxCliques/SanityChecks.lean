/-
Sanity checks for Rabern_HittingMaxCliques on K₃ (ω = 3, Δ = 2, 4ω ≥ 3(Δ+1);
a singleton independent set drops ω). Independent of the `sorry`.
-/
import Konigsberg.Literature.Coloring.Rabern_HittingMaxCliques.Statements
import Konigsberg.Literature.SanityLib

namespace Konigsberg.Literature.Coloring.Rabern_HittingMaxCliques

open Finset SimpleGraph Konigsberg.Literature.SanityLib

private abbrev G₃ := completeGraph (Fin 3)

example : 4 * G₃.cliqueNum ≥ 3 * (G₃.maxDegree + 1) := by
  have hω : G₃.cliqueNum = 3 := cliqueNum_completeGraph_fin 3
  have hΔ : G₃.maxDegree = 2 := by decide
  simp [hω, hΔ]

example : G₃.IsIndepSet ({(0 : Fin 3)} : Set (Fin 3)) := by
  intro a ha b hb
  simp at ha hb
  subst ha
  subst hb
  simp

end Konigsberg.Literature.Coloring.Rabern_HittingMaxCliques
