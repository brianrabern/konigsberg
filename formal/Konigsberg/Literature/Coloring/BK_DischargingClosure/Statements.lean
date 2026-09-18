/-
BK_DischargingClosure — discharging counterpart of `reducible_of_fChoosable`.

If every configuration in a finite set 𝒞 is reducible (absent from any
D-critical K_D-free graph) and 𝒞 is unavoidable (every D-critical K_D-free
graph contains some member of 𝒞), then there is no D-critical K_D-free graph.
Hence every graph with Δ = D and ω < D is (D−1)-colorable — Borodin–Kostochka
at D. The live regime is D = 9.

`Contains` abstracts “G contains some member of 𝒞”. Reducibility supplies
`¬ Contains` on any D-critical K_D-free G; unavoidability supplies `Contains`.
The composition is `False` — no such G exists.

`borodinKostochka_at_nine` is the Δ = 9 slice. It is definitionally distinct
from `BorodinKostochka.borodinKostochka` (which is Δ ≥ 9). A kernel proof of
the slice must not settle the general campaign.

Stated. Proofs deferred.
-/
import Mathlib.Combinatorics.SimpleGraph.Clique
import Konigsberg.Areas.Coloring.Basic

namespace Konigsberg.Literature.Coloring.BK_DischargingClosure

open SimpleGraph Konigsberg.Areas.Coloring

/-- No D-critical K_D-free graph exists. -/
def NoCriticalKDFree (D : ℕ) : Prop :=
  ∀ {V : Type*} [Fintype V] [DecidableEq V] (G : SimpleGraph V)
    [DecidableRel G.Adj], ¬ (KCritical G D ∧ G.cliqueNum < D)

variable {V : Type*} (G : SimpleGraph V)
variable [Fintype V] [DecidableEq V] [DecidableRel G.Adj]

/-- **reducible_and_unavoidable_imp_no_counterexample**
    (`BK.reducible_and_unavoidable_imp_no_counterexample`).

If `G` is D-critical and K_D-free, yet both avoids 𝒞 (`¬ Contains`) and must
meet 𝒞 (`Contains`), then `False` — no such `G` exists.

Until proved, UNAVOIDABLE Claims from `discharging_unavoidable` stay
conditional on this lemma. -/
theorem reducible_and_unavoidable_imp_no_counterexample
    (D : ℕ) (Contains : Prop)
    (hcrit : KCritical G D) (hω : G.cliqueNum < D)
    (hred : ¬ Contains) (hunav : Contains) : False := by
  sorry

/-- **Borodin–Kostochka at Δ = 9.** Every graph with Δ = 9 is
(max{8, ω})-colorable.

Distinct from `borodinKostochka` (Δ ≥ 9). Open. A durable `lean_prove` of this
statement is a Δ = 9 milestone, not general-campaign settlement. -/
theorem borodinKostochka_at_nine (hΔ : G.maxDegree = 9) :
    G.Colorable (max 8 G.cliqueNum) := by
  sorry

end Konigsberg.Literature.Coloring.BK_DischargingClosure
