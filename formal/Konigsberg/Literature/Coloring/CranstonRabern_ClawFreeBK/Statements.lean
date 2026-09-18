/-
CranstonRabern_ClawFreeBK — stated.

Every claw-free graph with Δ ≥ 9 is (max{ω, Δ−1})-colorable.
Equivalently: every claw-free graph with χ ≥ Δ ≥ 9 contains a K_Δ.
-/
import Mathlib.Combinatorics.SimpleGraph.Clique
import Konigsberg.Areas.Coloring.Basic

namespace Konigsberg.Literature.Coloring.CranstonRabern_ClawFreeBK

open SimpleGraph

variable {V : Type*} (G : SimpleGraph V)
variable [Fintype V] [DecidableEq V] [DecidableRel G.Adj]

/-- No induced claw K_{1,3}: three pairwise-nonadjacent neighbours of one vertex. -/
def ClawFree : Prop :=
  ∀ (v a b c : V),
    v ≠ a → v ≠ b → v ≠ c → a ≠ b → a ≠ c → b ≠ c →
    G.Adj v a → G.Adj v b → G.Adj v c →
    G.Adj a b ∨ G.Adj a c ∨ G.Adj b c

/-- Complete graphs are claw-free (any three neighbours of `v` form a triangle). -/
theorem completeGraph_clawFree (n : ℕ) : ClawFree (completeGraph (Fin n)) := by
  intro v a b c _ _ _ hab _ _ _ _ _
  exact Or.inl hab

/-- **Main theorem** (Cranston–Rabern, SIAM J. Discrete Math. 2013).

Every claw-free graph with Δ ≥ 9 satisfies χ ≤ max{ω, Δ−1}. -/
theorem clawFree_BK (hclaw : ClawFree G) (hΔ : 9 ≤ G.maxDegree) :
    G.Colorable (max (G.maxDegree - 1) G.cliqueNum) := by
  sorry

/-- Equivalent form: claw-free, χ ≥ Δ ≥ 9 ⇒ contains a K_Δ. -/
theorem clawFree_chi_ge_delta_contains_K_delta
    (hclaw : ClawFree G)
    (hΔ : 9 ≤ G.maxDegree)
    (hχ : ¬ G.Colorable (G.maxDegree - 1)) :
    G.maxDegree ≤ G.cliqueNum := by
  sorry

end Konigsberg.Literature.Coloring.CranstonRabern_ClawFreeBK
