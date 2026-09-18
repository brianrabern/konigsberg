/-
BorodinKostochka — stated (open).

The campaign target: χ ≤ max{Δ−1, ω} whenever Δ ≥ 9.
`Colorable k` is χ ≤ k. `max (maxDegree - 1) cliqueNum` is max{Δ−1, ω}.
-/
import Mathlib.Combinatorics.SimpleGraph.Clique
import Konigsberg.Areas.Coloring.Basic

namespace Konigsberg.Literature.Coloring.BorodinKostochka

open SimpleGraph

variable {V : Type*} (G : SimpleGraph V)
variable [Fintype V] [DecidableEq V] [DecidableRel G.Adj]

/-- **Borodin–Kostochka conjecture.** Every graph with Δ ≥ 9 is
(max{Δ−1, ω})-colorable.

Open. Reed proved a large-Δ case; the live regime is Δ = 9.
A durable `lean_prove` of this statement (no `sorry`) is campaign settlement. -/
theorem borodinKostochka (hΔ : 9 ≤ G.maxDegree) :
    G.Colorable (max (G.maxDegree - 1) G.cliqueNum) := by
  sorry

end Konigsberg.Literature.Coloring.BorodinKostochka
