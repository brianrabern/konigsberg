/-
Sanity checks for KostochkaCliqueGraph on K₃.
-/
import Konigsberg.Literature.Coloring.KostochkaCliqueGraph.Statements
import Konigsberg.Literature.SanityLib
import Mathlib.Data.Set.Card

namespace Konigsberg.Literature.Coloring.KostochkaCliqueGraph

open Set Finset SimpleGraph Konigsberg.Areas.Coloring Konigsberg.Literature.SanityLib

private abbrev G₃ := completeGraph (Fin 3)
private abbrev 𝒬₃ : Set (Finset (Fin 3)) := {(univ : Finset (Fin 3))}

example : 𝒬₃ ⊆ maxCliqueCollection G₃ := by
  intro s hs
  obtain rfl := eq_of_mem_singleton hs
  change G₃.IsNClique G₃.cliqueNum univ
  rw [cliqueNum_completeGraph_fin 3]
  decide

example : (2 * G₃.maxDegree + 2 : ℕ) < 3 * G₃.cliqueNum := by
  have hω : G₃.cliqueNum = 3 := cliqueNum_completeGraph_fin 3
  have hΔ : G₃.maxDegree = 2 := by decide
  simp [hω, hΔ]

example : (cliqueIntersectionGraph 𝒬₃).Connected :=
  Connected.of_subsingleton

example : (⋂ s ∈ 𝒬₃, (s : Set (Fin 3))).Nonempty := by
  refine ⟨0, ?_⟩
  simp [𝒬₃]

end Konigsberg.Literature.Coloring.KostochkaCliqueGraph
