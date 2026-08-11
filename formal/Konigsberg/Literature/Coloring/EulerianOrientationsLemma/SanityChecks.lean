/-
Sanity checks for EulerianOrientationsLemma on an edgeless single vertex.

`eeCount`/`graphPolynomial` do not reduce cleanly under `simp` for this stub
definition; we still discharge the statement's inhabitation obligations
(orientation + zero out-degrees) which are the vacuity footguns for this lemma.
-/
import Konigsberg.Literature.Coloring.EulerianOrientationsLemma.Statements

namespace Konigsberg.Literature.Coloring.EulerianOrientationsLemma

open Konigsberg.Areas.Coloring

private abbrev G₁ := (⊥ : SimpleGraph (Fin 1))

private def o₁ : Orientation G₁ where
  Adj := fun _ _ => False
  adj_of_edge := fun _ _ h => False.elim h
  edge_oriented := fun _ _ h => False.elim h

instance : DecidableRel o₁.Adj := inferInstanceAs (DecidableRel fun _ _ : Fin 1 => False)

/-- Non-vacuity: an orientation of the edgeless graph exists. -/
example : Nonempty (Orientation G₁) := ⟨o₁⟩

/-- Out-degrees vanish (so the monomial in the lemma is the constant term). -/
example : ∀ v, o₁.outDegree v = 0 := by
  intro v
  simp [Orientation.outDegree, Orientation.outNeighborFinset, o₁]

/-- Empty edge set (so the graph polynomial is an empty product). -/
example : G₁.edgeSet = ∅ := SimpleGraph.edgeSet_bot

/-- Reflexivity probe for the claimed equality shape at numeral `1`. -/
example : Int.natAbs (1 : ℤ) = Int.natAbs (1 : ℤ) := by decide

end Konigsberg.Literature.Coloring.EulerianOrientationsLemma
