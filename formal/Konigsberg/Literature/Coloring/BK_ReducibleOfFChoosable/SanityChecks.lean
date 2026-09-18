/-
Sanity checks for BK_ReducibleOfFChoosable — empty-graph f-choosability, and the
KCritical non-vacuity witness (K₃) so the ⇒ False wrapper is not vacuous.
-/
import Konigsberg.Literature.Coloring.BK_ReducibleOfFChoosable.Statements
import Konigsberg.Literature.Coloring.CompleteGraphKCritical.Proofs

namespace Konigsberg.Literature.Coloring.BK_ReducibleOfFChoosable

open SimpleGraph Konigsberg.Areas.Coloring

private abbrev G₀ := (⊥ : SimpleGraph PEmpty)

example : FChoosable G₀ (fun _ : PEmpty => 0) := by
  intro L _hL
  refine ⟨fun v => v.elim, fun v => v.elim, fun u _ _ => u.elim⟩

/-- Composed-hypothesis non-vacuity: `KCritical` is inhabited (K₃ is 3-critical). -/
example : KCritical (completeGraph (Fin 3)) 3 :=
  Konigsberg.Literature.Coloring.CompleteGraphKCritical.completeGraph_kCritical 3
    (by omega)

end Konigsberg.Literature.Coloring.BK_ReducibleOfFChoosable
