/-
Sanity checks for KostochkaYanceyKernelLemma on an edgeless single vertex.
-/
import Konigsberg.Literature.Coloring.KostochkaYanceyKernelLemma.Statements

namespace Konigsberg.Literature.Coloring.KostochkaYanceyKernelLemma

open Set SimpleGraph Konigsberg.Areas.Coloring

private abbrev G₁ := (⊥ : SimpleGraph (Fin 1))

private def s₁ : Superorientation G₁ where
  Adj := fun _ _ => False
  adj_of_edge := fun _ _ h => False.elim h
  covers := fun _ _ h => False.elim h

private abbrev I₁ : Set (Fin 1) := Set.univ

example : G₁.IsIndepSet I₁ := by
  intro x _ y _ _
  simp [bot_adj]

example : univ \ I₁ = (∅ : Set (Fin 1)) := by
  simp [I₁]

example : HasBackArrows G₁ s₁ ∅ := by
  intro u v hu hv _
  exact False.elim hu

example : HasBackArrows G₁ s₁ (univ \ I₁) := by
  rw [show univ \ I₁ = ∅ from by simp [I₁]]
  intro u v hu hv _
  exact False.elim hu

example : s₁.KernelPerfect := by
  intro S
  refine ⟨S, subset_rfl, ?_, ?_⟩
  · intro x _ y _ _
    simp [bot_adj]
  · intro v hvS hvI
    exact (hvI hvS).elim

end Konigsberg.Literature.Coloring.KostochkaYanceyKernelLemma
