/-
Sanity checks for CranstonLafayetteRabern_P5GemFreeBK.
Does not invoke the `sorry` theorem.
-/
import Konigsberg.Literature.Coloring.CranstonLafayetteRabern_P5GemFreeBK.Statements
import Konigsberg.Literature.SanityLib

namespace Konigsberg.Literature.Coloring.CranstonLafayetteRabern_P5GemFreeBK

open SimpleGraph Konigsberg.Literature.SanityLib

/-- P₅ is a path: consecutive vertices adjacent, distance-2 not. -/
example : p5Graph.Adj 0 1 := Or.inl rfl

example : ¬ p5Graph.Adj 0 2 := by
  intro h
  cases h with
  | inl h => cases h
  | inr h => cases h

/-- Gem: apex `0` meets the path; the P₄ ends are not adjacent. -/
example : gemGraph.Adj 0 1 := Or.inl ⟨rfl, by decide⟩

example : gemGraph.Adj 1 2 := Or.inr (Or.inr (Or.inl ⟨rfl, Nat.succ_pos 0⟩))

example : ¬ gemGraph.Adj 1 4 := by
  intro h
  rcases h with h | h | h | h
  · exact (by decide : (1 : Fin 5) ≠ 0) h.1
  · exact (by decide : (4 : Fin 5) ≠ 0) h.1
  · cases h.1
  · cases h.1

private abbrev G₁₀ := completeGraph (Fin 10)

/-- Non-vacuity of the Δ ≥ 9 side; K₁₀ is (P₅,gem)-free in the complete-graph
sense (any 5-set induces K₅, not P₅ or gem) but we only check the numeric
hypothesis here. -/
example : 9 ≤ G₁₀.maxDegree := by
  have hΔ : G₁₀.maxDegree = 9 := by decide
  simp [hΔ]

/-- Conclusion probe on K₁₀ without invoking the theorem. -/
example : max (G₁₀.maxDegree - 1) G₁₀.cliqueNum = 10 := by
  have hΔ : G₁₀.maxDegree = 9 := by decide
  have hω : G₁₀.cliqueNum = 10 := cliqueNum_completeGraph_fin 10
  simp [hΔ, hω]

end Konigsberg.Literature.Coloring.CranstonLafayetteRabern_P5GemFreeBK
