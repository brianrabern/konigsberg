/-
Sanity checks for Rabern_4ListCriticalEdgeBound (numerical + NotCompleteOfOrder).
-/
import Konigsberg.Literature.Coloring.Rabern_4ListCriticalEdgeBound.Statements
import Mathlib.Tactic.NormNum

namespace Konigsberg.Literature.Coloring.Rabern_4ListCriticalEdgeBound

open SimpleGraph

example : 4 ≤ (4 : ℕ) := by decide

example : denom 4 = 10 := by decide

example : NotCompleteOfOrder (⊥ : SimpleGraph (Fin 1)) 4 :=
  ⟨fun φ => by
    have := Fintype.card_congr φ.toEquiv
    simp at this⟩

example :
    2 * (completeGraph (Fin 8)).edgeFinset.card * denom 4 ≥
      ((4 - 1) * denom 4 + (4 - 3)) * Fintype.card (Fin 8) := by
  decide

example :
    2 * (completeGraph (Fin 2)).edgeFinset.card ≥
      (2 - 2) * Fintype.card (Fin 2) + 0 + 1 := by
  decide

end Konigsberg.Literature.Coloring.Rabern_4ListCriticalEdgeBound
