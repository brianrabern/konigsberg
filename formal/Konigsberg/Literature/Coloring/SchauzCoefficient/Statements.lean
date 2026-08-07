/-
SchauzCoefficient — stated.

Coefficient formula: if `∑ k_i = deg f` and `|A_i| = k_i+1`, then
`f_k = ∑_{a ∈ ∏ A} f(a) / N(a)`.
-/
import Mathlib.Algebra.MvPolynomial.Basic
import Mathlib.Algebra.MvPolynomial.Degrees
import Mathlib.Algebra.MvPolynomial.Eval
import Mathlib.Algebra.Field.Defs
import Mathlib.Data.Fintype.BigOperators

namespace Konigsberg.Literature.Coloring.SchauzCoefficient

open MvPolynomial Finset

variable {F : Type*} [Field F] {σ : Type*}

/-- Denominator `N(a) = ∏_i ∏_{b ∈ A_i \\ {a_i}} (a_i − b)`. -/
noncomputable def schauzDenom [Fintype σ] [DecidableEq F]
    (A : σ → Finset F) (a : σ → F) : F :=
  ∏ i : σ, ∏ b ∈ (A i).erase (a i), (a i - b)

/-- **SchauzCoefficient** (book §A coefficient formula). -/
theorem schauzCoefficient [Fintype σ] [DecidableEq σ] [DecidableEq F]
    (f : MvPolynomial σ F) (k : σ → ℕ)
    (hdeg : (∑ i : σ, k i) = f.totalDegree)
    (A : σ → Finset F) (hA : ∀ i, (A i).card = k i + 1) :
    coeff (Finsupp.equivFunOnFinite.symm k) f =
      ∑ a ∈ Fintype.piFinset A,
        eval (fun i => a i) f / schauzDenom A (fun i => a i) := by
  sorry

end Konigsberg.Literature.Coloring.SchauzCoefficient
