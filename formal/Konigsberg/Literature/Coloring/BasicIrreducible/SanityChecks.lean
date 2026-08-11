/-
Sanity checks for BasicIrreducible on the empty vertex set.
-/
import Konigsberg.Literature.Coloring.BasicIrreducible.Statements

namespace Konigsberg.Literature.Coloring.BasicIrreducible

open SimpleGraph Konigsberg.Areas.Coloring

private abbrev G₀ := (⊥ : SimpleGraph PEmpty)
private abbrev f₀ : PEmpty → ℤ := fun _ => 0

example : FIrreducible G₀ f₀ := by
  rintro ⟨_, _, ⟨x, _⟩, _⟩
  exact x.elim

example : ∀ v, f₀ v ≤ (G₀.degree v : ℤ) := fun v => v.elim

example : ∑ v : PEmpty, f₀ v ≤ 2 * (G₀.edgeFinset.card : ℤ) := by
  simp [f₀]

end Konigsberg.Literature.Coloring.BasicIrreducible
