/-
Sanity checks for KiersteadRabern_OreVizing.
-/
import Konigsberg.Literature.Coloring.KiersteadRabern_OreVizing.Statements
import Mathlib.Tactic.NormNum

namespace Konigsberg.Literature.Coloring.KiersteadRabern_OreVizing

open SimpleGraph
open Konigsberg.Areas.Coloring
open Konigsberg.Literature.Coloring.Rabern_4ListCriticalEdgeBound (NotCompleteOfOrder)

example : 6 ≤ (6 : ℕ) := by decide

example : NotCompleteOfOrder (⊥ : SimpleGraph (Fin 1)) 6 :=
  ⟨fun φ => by
    have := Fintype.card_congr φ.toEquiv
    simp at this⟩

example : alpha 6 = (1 : ℚ) / 2 - 1 / (20 : ℚ) := by
  simp only [alpha]
  norm_num

example : 18 ≤ (18 : ℕ) ∧ 2 * (1 : ℕ) ≤ 18 := by decide

example : Choosable (⊥ : SimpleGraph (Fin 1)) 1 :=
  choosable_card _

example :
    (2 * 45 : ℚ) ≥ gallaiBound 6 10 (edgeBoundC 6) := by
  simp only [gallaiBound, edgeBoundC, alpha]
  norm_num

end Konigsberg.Literature.Coloring.KiersteadRabern_OreVizing
