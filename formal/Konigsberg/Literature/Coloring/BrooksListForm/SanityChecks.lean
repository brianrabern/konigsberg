/-
Sanity checks for BrooksListForm on K₁.
-/
import Konigsberg.Literature.Coloring.BrooksListForm.Statements

namespace Konigsberg.Literature.Coloring.BrooksListForm

open Finset SimpleGraph Konigsberg.Areas.Coloring

private abbrev G₁ := (⊥ : SimpleGraph (Fin 1))

example : G₁.Connected := Connected.of_subsingleton

example : ¬ DegreeChoosable G₁ := by
  intro h
  obtain ⟨c, hc, _⟩ := h (fun _ => ∅) (fun _ => Nat.zero_le _)
  have : c 0 ∈ (∅ : Finset ℕ) := hc 0
  exact Finset.notMem_empty _ this

example : IsGallaiTree G₁ := by
  refine ⟨Connected.of_subsingleton, ?_⟩
  intro B hB
  left
  intro u hu v hv huv
  exact (huv (Subsingleton.elim u v)).elim

end Konigsberg.Literature.Coloring.BrooksListForm
