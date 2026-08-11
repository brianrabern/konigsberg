/-
Sanity checks for KernelPerfectSuperListBound on an edgeless single vertex.
-/
import Konigsberg.Literature.Coloring.KernelPerfectSuperListBound.Statements

namespace Konigsberg.Literature.Coloring.KernelPerfectSuperListBound

open Finset Set SimpleGraph Konigsberg.Areas.Coloring

private abbrev G₁ := (⊥ : SimpleGraph (Fin 1))

private def s₁ : Superorientation G₁ where
  Adj := fun _ _ => False
  adj_of_edge := fun _ _ h => False.elim h
  covers := fun _ _ h => False.elim h

instance : DecidableRel s₁.Adj := inferInstanceAs (DecidableRel fun _ _ : Fin 1 => False)

example : s₁.KernelPerfect := by
  intro S
  refine ⟨S, subset_rfl, ?_, ?_⟩
  · intro x _ y _ _
    simp [bot_adj]
  · intro v hvS hvI
    exact (hvI hvS).elim

private abbrev L₁ : ListAssignment (Fin 1) := fun _ => {0}

example : ∀ v, s₁.outDegree v < (L₁ v).card := by
  intro v
  have : s₁.outDegree v = 0 := by
    change Fintype.card {w // False} = 0
    simp
  simp [this, L₁]

example : ListColorable G₁ L₁ :=
  ⟨fun _ => 0, fun _ => by simp [L₁], fun _ _ h => False.elim ((bot_adj _ _).mp h)⟩

end Konigsberg.Literature.Coloring.KernelPerfectSuperListBound
