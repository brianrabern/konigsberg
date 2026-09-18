/-
Sanity checks for BK_DischargingClosure.
Does not invoke the `sorry` theorems.
-/
import Konigsberg.Literature.Coloring.BK_DischargingClosure.Statements
import Konigsberg.Literature.SanityLib

namespace Konigsberg.Literature.Coloring.BK_DischargingClosure

open SimpleGraph Konigsberg.Areas.Coloring Konigsberg.Literature.SanityLib

private abbrev G₀ := (⊥ : SimpleGraph PEmpty)
private abbrev G₉ := completeGraph (Fin 9)
private abbrev G₁₀ := completeGraph (Fin 10)

/-- Empty graph is 8-colorable, so not 9-critical (criticality is inhabitable as false). -/
example : G₀.Colorable 8 := by
  refine ⟨⟨fun v => v.elim, ?_⟩⟩
  intro v _w _h
  exact v.elim

example : ¬ KCritical G₀ 9 := by
  intro h
  have col : G₀.Colorable 8 := by
    refine ⟨⟨fun v => v.elim, ?_⟩⟩
    intro v _w _h
    exact v.elim
  exact h.1 col

/-- K₉ is not K₉-free: the H_BK clique bound can fail independently of criticality. -/
example : ¬ G₉.cliqueNum < 9 := by
  have h : G₉.cliqueNum = 9 := cliqueNum_completeGraph_fin 9
  simp [h]

/-- Conclusion probe for `borodinKostochka_at_nine` on K₁₀ (Δ = 9, ω = 10). -/
example : G₁₀.maxDegree = 9 := by decide

example : max 8 G₁₀.cliqueNum = 10 := by
  have hω : G₁₀.cliqueNum = 10 := cliqueNum_completeGraph_fin 10
  simp [hω]

end Konigsberg.Literature.Coloring.BK_DischargingClosure
