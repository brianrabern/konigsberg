/-
Sanity checks for DeltaEdgeColoring on an edgeless graph.
-/
import Konigsberg.Literature.Coloring.DeltaEdgeColoring.Statements

namespace Konigsberg.Literature.Coloring.DeltaEdgeColoring

open SimpleGraph Finset

private abbrev G₂ := (⊥ : SimpleGraph (Fin 2))

example : G₂.IsBipartite := by
  refine ⟨Coloring.mk (fun v : Fin 2 => v) ?_⟩
  intro u v h
  exact False.elim ((bot_adj u v).mp h)

example : G₂.maxDegree = 0 := by
  simp [maxDegree, degree]
  left
  decide

/-- Line graph of the empty graph is empty-vertex, hence `Colorable 0`. -/
example : G₂.lineGraph.Colorable G₂.maxDegree := by
  have hΔ : G₂.maxDegree = 0 := by
    simp [maxDegree, degree]
    left
    decide
  rw [hΔ]
  have : IsEmpty ↑G₂.edgeSet := by
    simpa [edgeSet_bot] using (inferInstance : IsEmpty Empty)
  -- edgeSet = ∅, so the subtype is empty
  haveI : IsEmpty G₂.edgeSet :=
    ⟨fun e => (by simpa [edgeSet_bot] using e.property : False)⟩
  refine ⟨Coloring.mk (fun e => isEmptyElim e) fun {e₁ e₂} _ => isEmptyElim e₁⟩

end Konigsberg.Literature.Coloring.DeltaEdgeColoring
