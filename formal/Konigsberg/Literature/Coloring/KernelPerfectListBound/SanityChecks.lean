/-
Sanity checks for KernelPerfectListBound on an edgeless single vertex.
-/
import Konigsberg.Literature.Coloring.KernelPerfectListBound.Statements

namespace Konigsberg.Literature.Coloring.KernelPerfectListBound

open Finset Set SimpleGraph Konigsberg.Areas.Coloring

private abbrev G₁ := (⊥ : SimpleGraph (Fin 1))

private def o₁ : Orientation G₁ where
  Adj := fun _ _ => False
  adj_of_edge := fun _ _ h => False.elim h
  edge_oriented := fun _ _ h => False.elim h

instance : DecidableRel o₁.Adj := inferInstanceAs (DecidableRel fun _ _ : Fin 1 => False)

example : o₁.KernelPerfect := by
  intro S
  refine ⟨S, subset_rfl, ?_, ?_⟩
  · intro x _ y _ _
    simp [bot_adj]
  · intro v hvS hvI
    exact (hvI hvS).elim

private abbrev L₁ : ListAssignment (Fin 1) := fun _ => {0}

example : ∀ v, o₁.outDegree v < (L₁ v).card := by
  intro v
  have : o₁.outDegree v = 0 := by
    simp [Orientation.outDegree, Orientation.outNeighborFinset, o₁]
  simp [this, L₁]

example : ListColorable G₁ L₁ :=
  ⟨fun _ => 0, fun _ => by simp [L₁], fun _ _ h => False.elim ((bot_adj _ _).mp h)⟩

end Konigsberg.Literature.Coloring.KernelPerfectListBound
