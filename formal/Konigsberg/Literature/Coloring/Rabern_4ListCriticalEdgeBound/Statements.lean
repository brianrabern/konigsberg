/-
Rabern_4ListCriticalEdgeBound — Main Theorem from
`github.com/landon/Research/4ListCriticalEdgeBound` (EJC version).

Every non-complete k-list-critical graph has average degree at least
  k − 1 + (k − 3)/(k² − 2k + 2).

Statements typecheck; proofs deferred (`status = "stated"`). Depends on
`KListCritical` (`Areas/Coloring/Basic`) and will eventually need
`basicIrreducible` / Kernel Magic for the discharging argument.
-/
import Mathlib.Combinatorics.SimpleGraph.Maps
import Konigsberg.Areas.Coloring.Basic

namespace Konigsberg.Literature.Coloring.Rabern_4ListCriticalEdgeBound

open Finset SimpleGraph
open Konigsberg.Areas.Coloring

variable {V : Type*} (G : SimpleGraph V)
variable [Fintype V] [DecidableEq V] [DecidableRel G.Adj]

/-! ### Auxiliary notions from the paper -/

/-- Number of edges with one end in `I` and one end outside `I`. -/
noncomputable def cutSize (I : Finset V) : ℕ :=
  #{e ∈ G.edgeFinset | ∃ u ∈ I, ∃ v ∉ I, e = s(u, v)}

/-- Maximum independent cover number `mic(G)`: max of `‖I, V∖I‖` over
independent sets `I` (Rabern, Def.; Kierstead–Rabern Kernel Magic). -/
noncomputable def mic : ℕ :=
  sSup {cutSize G I | (I : Finset V) (_ : G.IsIndepSet (I : Set V))}

/-- Denominator appearing in the Main Theorem bound. Always ≥ 1. -/
def denom (k : ℕ) : ℕ := k ^ 2 - 2 * k + 2

/-- `G` is not isomorphic to the complete graph `K_k`. -/
def NotCompleteOfOrder (k : ℕ) : Prop :=
  IsEmpty (G ≃g completeGraph (Fin k))

/-! ### Main Theorem (stated) -/

/-- **Main Theorem** (Rabern, *A better lower bound on average degree of
4-list-critical graphs*, Elec. J. Combin. 2016).

Every non-complete `k`-list-critical graph has average degree at least
`k - 1 + (k - 3) / (k² - 2k + 2)`.

Stated in cleared-denominator form:
`2 |E| · denom(k) ≥ ((k-1)·denom(k) + (k-3)) · |V|`. -/
theorem averageDegree_listCritical {k : ℕ} (hk : 4 ≤ k)
    (hcrit : KListCritical G k) (hne : NotCompleteOfOrder G k) :
    2 * G.edgeFinset.card * denom k ≥
      ((k - 1) * denom k + (k - 3)) * Fintype.card V := by
  sorry

/-- **Kernel Magic** (Kierstead–Rabern): every `k`-list-critical graph
satisfies `2‖G‖ ≥ (k-2)|G| + mic(G) + 1`. Primary tool for the Main Theorem. -/
theorem kernelMagic {k : ℕ} (hk : 1 ≤ k) (hcrit : KListCritical G k) :
    2 * G.edgeFinset.card ≥ (k - 2) * Fintype.card V + mic G + 1 := by
  sorry

end Konigsberg.Literature.Coloring.Rabern_4ListCriticalEdgeBound
