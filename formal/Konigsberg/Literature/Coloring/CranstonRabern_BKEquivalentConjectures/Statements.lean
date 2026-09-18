/-
CranstonRabern_BKEquivalentConjectures — stated.

Headline: certain weaker-looking conjectures are equivalent to Borodin–Kostochka.
The working equivalent used here is: every graph with χ = Δ = 9 contains a
(not necessarily induced) copy of the join K₃ ∗ Ē₆.

The paper's engine is the classification of joins A ∗ B (|A|,|B| ≥ 2) that are
f-choosable for f(v) = d(v)−1; such a join cannot be an induced subgraph of a
vertex-critical graph with χ = Δ. That exclusion is the second stated theorem.
The full join-classification table is *not* encoded.
-/
import Mathlib.Combinatorics.SimpleGraph.Maps
import Konigsberg.Areas.Coloring.Basic

namespace Konigsberg.Literature.Coloring.CranstonRabern_BKEquivalentConjectures

open Konigsberg.Areas.Coloring
open SimpleGraph

variable {α β : Type*}

/-- Disjoint union of `G` and `H` plus all cross edges (the join `G ∗ H`). -/
def graphJoin (G : SimpleGraph α) (H : SimpleGraph β) : SimpleGraph (α ⊕ β) where
  Adj
    | .inl a, .inl b => G.Adj a b
    | .inr a, .inr b => H.Adj a b
    | .inl _, .inr _ => True
    | .inr _, .inl _ => True
  symm := by
    refine ⟨fun x y h => ?_⟩
    cases x with
    | inl _ =>
      cases y with
      | inl _ => exact h.symm
      | inr _ => trivial
    | inr _ =>
      cases y with
      | inl _ => trivial
      | inr _ => exact h.symm
  loopless := by
    refine ⟨fun x h => ?_⟩
    cases x with
    | inl _ => exact SimpleGraph.irrefl (G := G) h
    | inr _ => exact SimpleGraph.irrefl (G := H) h

/-- The join `K₃ ∗ Ē₆` (triangle completely joined to an independent set of size 6). -/
abbrev K3JoinE6 : SimpleGraph (Fin 3 ⊕ Fin 6) :=
  graphJoin (completeGraph (Fin 3)) (⊥ : SimpleGraph (Fin 6))

/-- Ordinary BK: Δ ≥ 9 ⇒ χ ≤ max{ω, Δ−1}. -/
def BKStatement : Prop :=
  ∀ {V : Type*} [Fintype V] (G : SimpleGraph V) [DecidableRel G.Adj],
    9 ≤ G.maxDegree → G.Colorable (max G.cliqueNum (G.maxDegree - 1))

/-- Apparent weakening: every graph with χ = Δ = 9 contains a copy of `K₃ ∗ Ē₆`
as a subgraph (paper Conjecture 1.17 / abstract). -/
def ContainsK3JoinE6 : Prop :=
  ∀ {V : Type*} [Fintype V] (G : SimpleGraph V) [DecidableRel G.Adj],
    G.maxDegree = 9 → ¬ G.Colorable 8 → Nonempty (K3JoinE6 ↪g G)

/-- **Main equivalence** (Cranston–Rabern, European J. Combin. 2015).

BK is equivalent to “χ = Δ = 9 ⇒ contains K₃ ∗ Ē₆ as a subgraph”. Other
equivalent weakenings in the paper (joins A₁ ∗ A₂ with size constraints) are
not encoded here. -/
theorem equivalent_K3_join_E6 : BKStatement ↔ ContainsK3JoinE6 := by
  sorry

variable {V : Type*} (G : SimpleGraph V)
variable [Fintype V] [DecidableEq V] [DecidableRel G.Adj]

/-- An `f`-choosable join with `f(v) = d(v)−1` and both sides at least two
vertices cannot appear as an *induced* subgraph of a `D`-critical graph with
Δ = D. This is the paper's structural engine (Section 4), stated for a single
join rather than the classified list. -/
theorem fChoosable_join_not_induced_in_critical
    {α' β' : Type*} [Fintype α'] [Fintype β']
    (A : SimpleGraph α') (B : SimpleGraph β')
    [DecidableRel A.Adj] [DecidableRel B.Adj]
    [DecidableRel (graphJoin A B).Adj]
    (hα : 2 ≤ Fintype.card α') (hβ : 2 ≤ Fintype.card β')
    (hf : FChoosable (graphJoin A B) (fun v => (graphJoin A B).degree v - 1))
    (D : ℕ) (hcrit : KCritical G D) (hΔ : G.maxDegree = D) :
    ¬ ∃ s : Set V, Nonempty (G.induce s ≃g graphJoin A B) := by
  sorry

end Konigsberg.Literature.Coloring.CranstonRabern_BKEquivalentConjectures
