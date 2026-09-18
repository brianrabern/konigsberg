/-
SanityChecks for CompleteGraphKCritical — independent probes, no `decide` on
`Colorable` (that Prop is not a `Decidable`).
-/
import Konigsberg.Areas.Coloring.Basic

namespace Konigsberg.Literature.Coloring.CompleteGraphKCritical

open SimpleGraph

/-- Conclusion probe: K₃ is genuinely not 2-colorable (so `KCritical 3`'s first
conjunct is non-trivial). Independent of the main theorem. -/
example : ¬ (completeGraph (Fin 3)).Colorable 2 := by
  intro hc
  have hle : Nat.card (Fin 3) ≤ 2 :=
    hc.card_le_of_pairwise_adj id fun i j hij => by
      simp [completeGraph_eq_top, top_adj, hij]
  simp [Nat.card_eq_fintype_card, Fintype.card_fin] at hle

/-- Non-vacuity of the hypothesis at k = 3: K₃ exists and is 3-colorable (the
critical value), so `KCritical 3` is not vacuously unsatisfiable at the top. -/
example : (completeGraph (Fin 3)).Colorable 3 := by
  simpa using colorable_of_fintype (completeGraph (Fin 3))

end Konigsberg.Literature.Coloring.CompleteGraphKCritical
