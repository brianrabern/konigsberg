/-
Sanity checks for CombinatorialNullstellensatz on `X : ℚ[X]` (one variable).
-/
import Konigsberg.Literature.Coloring.CombinatorialNullstellensatz.Statements
import Mathlib.Tactic.NormNum

namespace Konigsberg.Literature.Coloring.CombinatorialNullstellensatz

open MvPolynomial Finset

noncomputable section

private abbrev σ := Fin 1
private noncomputable def f : MvPolynomial σ ℚ := X (0 : σ)
private def k : σ → ℕ := fun _ => 1
private def A : σ → Finset ℚ := fun _ => {0, 1}

example : (∑ i : σ, k i) = f.totalDegree := by
  simp [k, f, totalDegree_X]

example : coeff (Finsupp.single (0 : σ) 1) f ≠ 0 := by
  simp [f]

example : ∀ i, k i + 1 ≤ (A i).card := by
  intro i; simp [k, A]

example : ∃ x : σ → ℚ, (∀ i, x i ∈ A i) ∧ eval x f ≠ 0 := by
  refine ⟨fun _ => (1 : ℚ), ?_, ?_⟩
  · intro i; simp [A]
  · simp [f]

end

end Konigsberg.Literature.Coloring.CombinatorialNullstellensatz
