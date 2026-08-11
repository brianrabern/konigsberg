/-
Sanity checks for FirstListBound on an edgeless single vertex.
-/
import Konigsberg.Literature.Coloring.RabernBook_FirstListBound.Statements

namespace Konigsberg.Literature.Coloring.RabernBook_FirstListBound

open Finset SimpleGraph Konigsberg.Areas.Coloring

private abbrev G₁ := (⊥ : SimpleGraph (Fin 1))
private abbrev L₁ : ListAssignment (Fin 1) := fun _ => {0}

example : ∀ v, G₁.degree v + 1 ≤ (L₁ v).card := by
  intro v
  have : G₁.degree v = 0 := by simp [degree]
  simp [this, L₁]

example : ListColorable G₁ L₁ :=
  ⟨fun _ => 0, fun _ => by simp [L₁], fun _ _ h => False.elim ((bot_adj _ _).mp h)⟩

end Konigsberg.Literature.Coloring.RabernBook_FirstListBound
