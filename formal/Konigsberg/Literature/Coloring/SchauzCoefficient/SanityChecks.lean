/-
Sanity checks for SchauzCoefficient on the constant polynomial `1`.
-/
import Konigsberg.Literature.Coloring.SchauzCoefficient.Statements
import Mathlib.Tactic.NormNum

namespace Konigsberg.Literature.Coloring.SchauzCoefficient

open MvPolynomial Finset

noncomputable section

private abbrev σ := Fin 1
private noncomputable def f : MvPolynomial σ ℚ := C 1
private def k : σ → ℕ := fun _ => 0
private def A : σ → Finset ℚ := fun _ => {0}

example : (∑ i : σ, k i) = f.totalDegree := by
  simp [k, f]

example : ∀ i, (A i).card = k i + 1 := by
  intro i; simp [A, k]

example : coeff (0 : σ →₀ ℕ) f = 1 := by
  simp [f]

example : schauzDenom A (fun _ => (0 : ℚ)) = 1 := by
  simp [schauzDenom, A]

end

end Konigsberg.Literature.Coloring.SchauzCoefficient
