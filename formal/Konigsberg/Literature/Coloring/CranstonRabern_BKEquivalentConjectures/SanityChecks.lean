/-
Sanity checks for CranstonRabern_BKEquivalentConjectures.
Does not invoke the `sorry` theorems.
-/
import Konigsberg.Literature.Coloring.CranstonRabern_BKEquivalentConjectures.Statements

namespace Konigsberg.Literature.Coloring.CranstonRabern_BKEquivalentConjectures

open SimpleGraph

/-- The join `K₃ ∗ Ē₆` has nine vertices. -/
example : Fintype.card (Fin 3 ⊕ Fin 6) = 9 := by decide

/-- Cross edges of the join are present; the independent side has no edges. -/
example : K3JoinE6.Adj (.inl 0) (.inr 0) := trivial

example : ¬ K3JoinE6.Adj (.inr 0) (.inr 1) := by
  simp [K3JoinE6, graphJoin]

/-- The triangle side of the join is a clique. -/
example : K3JoinE6.Adj (.inl 0) (.inl 1) := by
  simp [K3JoinE6, graphJoin, completeGraph]

end Konigsberg.Literature.Coloring.CranstonRabern_BKEquivalentConjectures
