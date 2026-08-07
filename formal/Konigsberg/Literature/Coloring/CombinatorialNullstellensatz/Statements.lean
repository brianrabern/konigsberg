/-
CombinatorialNullstellensatz — stated (Alon's combinatorial Nullstellensatz).

Formal hook for the coefficient criterion used by Alon–Tarsi / graph polynomials.
-/
import Mathlib.Algebra.MvPolynomial.Basic
import Mathlib.Algebra.MvPolynomial.Degrees
import Mathlib.Algebra.MvPolynomial.Eval
import Mathlib.Algebra.Field.Defs

namespace Konigsberg.Literature.Coloring.CombinatorialNullstellensatz

open MvPolynomial

variable {F : Type*} [Field F] {σ : Type*}

/-- **Combinatorial Nullstellensatz** (book, unlabeled lemma opening the CN chapter).

If `f ∈ F[x_i]`, `∑ k_i = deg f`, and the coefficient of `∏ x_i^{k_i}` is nonzero,
then for any sets `A_i` with `|A_i| ≥ k_i+1` there is a point of `∏ A_i` where `f ≠ 0`. -/
theorem combinatorialNullstellensatz [Fintype σ] [DecidableEq σ]
    (f : MvPolynomial σ F) (k : σ → ℕ)
    (hdeg : (∑ i : σ, k i) = f.totalDegree)
    (hcoeff : coeff (Finsupp.equivFunOnFinite.symm k) f ≠ 0)
    (A : σ → Finset F) (hA : ∀ i, k i + 1 ≤ (A i).card) :
    ∃ x : σ → F, (∀ i, x i ∈ A i) ∧ eval x f ≠ 0 := by
  sorry

end Konigsberg.Literature.Coloring.CombinatorialNullstellensatz
