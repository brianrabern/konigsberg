/-
CranstonLafayetteRabern_P5GemFreeBK — stated.

BK for (P₅, gem)-free graphs: no induced P₅ and no induced gem (K₁ ∨ P₄).
-/
import Mathlib.Combinatorics.SimpleGraph.Clique
import Mathlib.Combinatorics.SimpleGraph.Maps
import Konigsberg.Areas.Coloring.Basic

namespace Konigsberg.Literature.Coloring.CranstonLafayetteRabern_P5GemFreeBK

open SimpleGraph

/-- The path P₅ on vertices `0—1—2—3—4`. -/
def p5Graph : SimpleGraph (Fin 5) where
  Adj i j := i.val + 1 = j.val ∨ j.val + 1 = i.val
  symm := by
    refine ⟨fun x y h => ?_⟩
    cases h with
    | inl h => exact Or.inr h
    | inr h => exact Or.inl h
  loopless := by
    refine ⟨fun x h => ?_⟩
    cases h with
    | inl h => exact (Nat.succ_ne_self x.val) h
    | inr h => exact (Nat.succ_ne_self x.val) h

/-- The gem: join of K₁ with P₄ (apex `0` completely joined to path `1—2—3—4`). -/
def gemGraph : SimpleGraph (Fin 5) where
  Adj i j :=
    (i = 0 ∧ j ≠ 0) ∨ (j = 0 ∧ i ≠ 0) ∨
      (i.val + 1 = j.val ∧ 0 < i.val) ∨ (j.val + 1 = i.val ∧ 0 < j.val)
  symm := by
    refine ⟨fun x y h => ?_⟩
    rcases h with h | h | h | h
    · exact Or.inr (Or.inl h)
    · exact Or.inl h
    · exact Or.inr (Or.inr (Or.inr h))
    · exact Or.inr (Or.inr (Or.inl h))
  loopless := by
    refine ⟨fun x h => ?_⟩
    rcases h with h | h | h | h
    · exact h.2 h.1
    · exact h.2 h.1
    · exact (Nat.succ_ne_self x.val) h.1
    · exact (Nat.succ_ne_self x.val) h.1

variable {V : Type*} (G : SimpleGraph V)
variable [Fintype V] [DecidableEq V] [DecidableRel G.Adj]

/-- No induced P₅ and no induced gem. -/
def P5GemFree : Prop :=
  (∀ s : Set V, ¬ Nonempty ((G.induce s) ≃g p5Graph)) ∧
    (∀ s : Set V, ¬ Nonempty ((G.induce s) ≃g gemGraph))

/-- **Main theorem** (Cranston–Lafayette–Rabern, J. Graph Theory 2022).

Every (P₅, gem)-free graph with Δ ≥ 9 satisfies χ ≤ max{ω, Δ−1}. -/
theorem p5GemFree_BK (hfree : P5GemFree G) (hΔ : 9 ≤ G.maxDegree) :
    G.Colorable (max (G.maxDegree - 1) G.cliqueNum) := by
  sorry

end Konigsberg.Literature.Coloring.CranstonLafayetteRabern_P5GemFreeBK
