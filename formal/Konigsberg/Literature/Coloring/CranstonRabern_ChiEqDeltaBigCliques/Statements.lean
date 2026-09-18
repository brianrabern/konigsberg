/-
CranstonRabern_ChiEqDeltaBigCliques — stated.

Main theorem: Δ ≥ 13 and χ ≥ Δ ⇒ ω ≥ Δ−3.
(Equivalently: Δ ≥ 13 and ω ≤ Δ−4 ⇒ χ ≤ Δ−1.)

Second theorem: if χ ≥ Δ then either ω ≥ Δ or the subgraph induced by
degree-Δ vertices has clique number at least Δ−5.
-/
import Mathlib.Combinatorics.SimpleGraph.Clique
import Konigsberg.Areas.Coloring.Basic

namespace Konigsberg.Literature.Coloring.CranstonRabern_ChiEqDeltaBigCliques

open SimpleGraph

variable {V : Type*} (G : SimpleGraph V)
variable [Fintype V] [DecidableEq V] [DecidableRel G.Adj]

/-- Vertices of degree Δ(G). -/
def highVertices : Set V := {v | G.degree v = G.maxDegree}

/-- **Main Theorem** (Cranston–Rabern, SIAM J. Discrete Math. 2015).

If Δ ≥ 13 and χ ≥ Δ, then ω ≥ Δ−3. `χ ≥ Δ` is `¬ Colorable (Δ−1)`. -/
theorem chi_ge_delta_implies_omega_ge_delta_sub_three
    (hΔ : 13 ≤ G.maxDegree)
    (hχ : ¬ G.Colorable (G.maxDegree - 1)) :
    G.maxDegree - 3 ≤ G.cliqueNum := by
  sorry

/-- If χ ≥ Δ then either ω ≥ Δ, or the high-vertex subgraph has ω ≥ Δ−5. -/
theorem chi_ge_delta_omega_or_high
    (hχ : ¬ G.Colorable (G.maxDegree - 1)) :
    G.maxDegree ≤ G.cliqueNum ∨
      G.maxDegree - 5 ≤ (G.induce (highVertices G)).cliqueNum := by
  sorry

end Konigsberg.Literature.Coloring.CranstonRabern_ChiEqDeltaBigCliques
