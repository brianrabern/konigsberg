/-
Sanity checks for HajnalLemma: confirms non-vacuity and the fixed statement at
K₃ with 𝒬 = {univ} (independent of the `sorry` proof). Does not probe the
empty-𝒬 edge case — that missing-hypothesis failure is outside what a single
concrete witness can guarantee; see docs/TRUST.md.
-/
import Konigsberg.Literature.Coloring.HajnalLemma.Statements
import Konigsberg.Literature.SanityLib
import Mathlib.Data.Set.Card
import Mathlib.Tactic.NormNum

namespace Konigsberg.Literature.Coloring.HajnalLemma

open Set Finset SimpleGraph Konigsberg.Areas.Coloring Konigsberg.Literature.SanityLib

private abbrev G := completeGraph (Fin 3)
private abbrev Q : Set (Finset (Fin 3)) := {(univ : Finset (Fin 3))}

/-- Non-vacuity: singleton collection is nonempty. -/
example : Q.Nonempty := singleton_nonempty _

/-- Non-vacuity: univ is a maximum clique of K₃. -/
example : Q ⊆ maxCliqueCollection G := by
  intro s hs
  obtain rfl := eq_of_mem_singleton hs
  change G.IsNClique G.cliqueNum univ
  rw [cliqueNum_completeGraph_fin 3]
  decide

/-- Conclusion on the same instance (without invoking `hajnalLemma`). -/
example :
    (⋃ s ∈ Q, (s : Set (Fin 3))).ncard + (⋂ s ∈ Q, (s : Set (Fin 3))).ncard ≥
      2 * G.cliqueNum := by
  rw [cliqueNum_completeGraph_fin 3]
  simp [Q, ncard_univ, Nat.card_eq_fintype_card, Fintype.card_fin]

end Konigsberg.Literature.Coloring.HajnalLemma
