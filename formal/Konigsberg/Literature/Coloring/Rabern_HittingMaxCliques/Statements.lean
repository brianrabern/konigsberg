/-
Rabern_HittingMaxCliques — stated.

If ω(G) ≥ (3/4)(Δ(G)+1), then G has an independent set I with ω(G−I) < ω(G)
(equivalently: I meets every maximum clique). Threshold is 3/4, not 2/3.
-/
import Mathlib.Combinatorics.SimpleGraph.Clique
import Mathlib.Combinatorics.SimpleGraph.Finite

namespace Konigsberg.Literature.Coloring.Rabern_HittingMaxCliques

open SimpleGraph

variable {V : Type*} (G : SimpleGraph V)
variable [Fintype V] [DecidableEq V] [DecidableRel G.Adj]

/-- **Hitting maximum cliques** (Rabern, J. Graph Theory 2011).

`4ω ≥ 3(Δ+1)` is the ℕ form of ω ≥ (3/4)(Δ+1). The independent set I
satisfies ω(G[V\I]) < ω(G). -/
theorem hitting_max_cliques
    (hω : 4 * G.cliqueNum ≥ 3 * (G.maxDegree + 1)) :
    ∃ I : Finset V, G.IsIndepSet (I : Set V) ∧
      (G.induce (Iᶜ : Set V)).cliqueNum < G.cliqueNum := by
  sorry

end Konigsberg.Literature.Coloring.Rabern_HittingMaxCliques
