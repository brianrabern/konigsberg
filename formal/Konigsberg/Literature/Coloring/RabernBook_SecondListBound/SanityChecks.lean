/-
Sanity checks for SecondListBound on an edgeless single vertex.
-/
import Konigsberg.Literature.Coloring.RabernBook_SecondListBound.Statements

namespace Konigsberg.Literature.Coloring.RabernBook_SecondListBound

open Finset SimpleGraph Konigsberg.Areas.Coloring

private abbrev G₁ := (⊥ : SimpleGraph (Fin 1))

private def o₁ : Orientation G₁ where
  Adj := fun _ _ => False
  adj_of_edge := fun _ _ h => False.elim h
  edge_oriented := fun _ _ h => False.elim h

instance : DecidableRel o₁.Adj := inferInstanceAs (DecidableRel fun _ _ : Fin 1 => False)

example : o₁.IsAcyclic :=
  WellFounded.intro fun _ => Acc.intro _ fun _ h => False.elim h

private abbrev L₁ : ListAssignment (Fin 1) := fun _ => {0}

example : ∀ v, o₁.outDegree v + 1 ≤ (L₁ v).card := by
  intro v
  have : o₁.outDegree v = 0 := by
    simp [Orientation.outDegree, Orientation.outNeighborFinset, o₁]
  simp [this, L₁]

example : ListColorable G₁ L₁ :=
  ⟨fun _ => 0, fun _ => by simp [L₁], fun _ _ h => False.elim ((bot_adj _ _).mp h)⟩

end Konigsberg.Literature.Coloring.RabernBook_SecondListBound
