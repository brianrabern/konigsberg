/-
CranstonRabern_ImprovedEdgeBound — discharging edge lower bounds for
k-AT-critical graphs (hence list-critical).

Source: `github.com/landon/Research/ImprovedEdgeBound/EdgeBoundDischargingFinal.tex`
(arXiv:1602.02589). Public domain. Statements typecheck; proofs deferred.
-/
import Mathlib.Combinatorics.SimpleGraph.Maps
import Konigsberg.Areas.Coloring.Basic
import Konigsberg.Literature.Coloring.Rabern_4ListCriticalEdgeBound.Statements

namespace Konigsberg.Literature.Coloring.CranstonRabern_ImprovedEdgeBound

open SimpleGraph
open Konigsberg.Areas.Coloring
open Konigsberg.Literature.Coloring.Rabern_4ListCriticalEdgeBound
  (NotCompleteOfOrder)

variable {V : Type*} (G : SimpleGraph V)
variable [Fintype V] [DecidableEq V] [DecidableRel G.Adj]

/-! ### AT-criticality stub -/

/-- Abstract predicate: `G` is `k`-AT-critical
(`AT(G) = k` and `AT(H) < k` for every proper subgraph `H`).

No instances yet — replace with a real definition once the Alon–Tarsi number
lands in `Areas/Coloring`. Theorems below take this as a typeclass hypothesis
so they typecheck as the published statements. -/
class IsKATCritical {V : Type*} (G : SimpleGraph V) (k : ℕ) : Prop

/-! ### Main corollaries (Cranston–Rabern) -/

/-- Denominator for the `k ≥ 7` Main Corollary. -/
def denomMain (k : ℕ) : ℕ := k ^ 3 + k ^ 2 - 15 * k + 15

/-- Denominator for the `k ∈ {5,6}` Minor Corollary. -/
def denomMinor (k : ℕ) : ℕ := k ^ 3 + 2 * k ^ 2 - 18 * k + 15

/-- **MainCor** (Cranston–Rabern, arXiv:1602.02589).

If `G` is `k`-AT-critical, `k ≥ 7`, `G ≠ K_k`, then
`d(G) ≥ k−1 + (k−3)(2k−5) / (k³ + k² − 15k + 15)`.

Cleared form: `2|E| · D ≥ ((k−1)·D + (k−3)(2k−5)) · |V|`. -/
theorem mainCor {k : ℕ} [IsKATCritical G k] (hk : 7 ≤ k)
    (hne : NotCompleteOfOrder G k) :
    2 * G.edgeFinset.card * denomMain k ≥
      ((k - 1) * denomMain k + (k - 3) * (2 * k - 5)) * Fintype.card V := by
  sorry

/-- **MinorCor** — same shape for `k ∈ {5,6}` with the alternate denominator
`k³ + 2k² − 18k + 15`. -/
theorem minorCor {k : ℕ} [IsKATCritical G k] (hk : k = 5 ∨ k = 6)
    (hne : NotCompleteOfOrder G k) :
    2 * G.edgeFinset.card * denomMinor k ≥
      ((k - 1) * denomMinor k + (k - 3) * (2 * k - 5)) * Fintype.card V := by
  sorry

end Konigsberg.Literature.Coloring.CranstonRabern_ImprovedEdgeBound
