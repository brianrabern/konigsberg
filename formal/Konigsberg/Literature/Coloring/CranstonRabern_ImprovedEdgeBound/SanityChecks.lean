/-
Sanity checks for CranstonRabern_ImprovedEdgeBound.
-/
import Konigsberg.Literature.Coloring.CranstonRabern_ImprovedEdgeBound.Statements
import Mathlib.Tactic.NormNum

namespace Konigsberg.Literature.Coloring.CranstonRabern_ImprovedEdgeBound

open SimpleGraph
open Konigsberg.Literature.Coloring.Rabern_4ListCriticalEdgeBound (NotCompleteOfOrder)

private abbrev G₈ := completeGraph (Fin 8)

instance : IsKATCritical G₈ 7 := ⟨⟩

example : 7 ≤ (7 : ℕ) := by decide

example : NotCompleteOfOrder G₈ 7 :=
  ⟨fun φ => by
    have := Fintype.card_congr φ.toEquiv
    simp at this⟩

example : denomMain 7 = 302 := by decide

example :
    2 * G₈.edgeFinset.card * denomMain 7 ≥
      ((7 - 1) * denomMain 7 + (7 - 3) * (2 * 7 - 5)) * Fintype.card (Fin 8) := by
  decide

instance instAT5 : IsKATCritical G₈ 5 := ⟨⟩

example : (5 : ℕ) = 5 ∨ (5 : ℕ) = 6 := Or.inl rfl

example : NotCompleteOfOrder G₈ 5 :=
  ⟨fun φ => by
    have := Fintype.card_congr φ.toEquiv
    simp at this⟩

example :
    2 * G₈.edgeFinset.card * denomMinor 5 ≥
      ((5 - 1) * denomMinor 5 + (5 - 3) * (2 * 5 - 5)) * Fintype.card (Fin 8) := by
  decide

end Konigsberg.Literature.Coloring.CranstonRabern_ImprovedEdgeBound
