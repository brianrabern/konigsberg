/-
CranstonRabern_BrooksAndBeyond — stated.

Preferred Brooks formulation from the survey: χ ≤ max{3, ω, Δ}.
Theorem 8.3: the same bound for χ_ℓ. Lemma 8.1: Δ ≥ 3 and no K_{Δ+1}
implies α ≥ n/Δ. Degree-choosable classification is `BrooksListForm`
(Theorem 9.1); not restated here.
-/
import Mathlib.Combinatorics.SimpleGraph.Clique
import Konigsberg.Areas.Coloring.Basic

namespace Konigsberg.Literature.Coloring.CranstonRabern_BrooksAndBeyond

open Konigsberg.Areas.Coloring
open SimpleGraph

variable {V : Type*} (G : SimpleGraph V)
variable [Fintype V] [DecidableEq V] [DecidableRel G.Adj]

/-- Preferred Brooks bound in the survey: χ ≤ max{3, ω, Δ}.

Equivalent to classical Brooks (odd cycles are the Δ = 2, ω = 2 case).
Distinct from EXTERNAL `BrooksLean`, which uses the ¬Δ-colorable ⇒ K_{Δ+1}
or odd-cycle form. -/
theorem brooks_max3 :
    G.Colorable (max 3 (max G.cliqueNum G.maxDegree)) := by
  sorry

/-- **Theorem 8.3.** Every graph satisfies χ_ℓ ≤ max{3, ω, Δ}. -/
theorem list_brooks_max3 :
    Choosable G (max 3 (max G.cliqueNum G.maxDegree)) := by
  sorry

/-- **Journal Lemma 8.1 / arXiv Lemma 8.** If Δ ≥ 3 and G contains no K_{Δ+1},
then α ≥ |G|/Δ.

Encoded as: some independent set I with Δ · |I| ≥ n. The arXiv wording
omits Δ ≥ 3, which is required (odd cycles). -/
theorem independence_when_K_delta_free
    (hΔ : 3 ≤ G.maxDegree) (hω : G.cliqueNum ≤ G.maxDegree) :
    ∃ I : Finset V, G.IsIndepSet (I : Set V) ∧
      G.maxDegree * I.card ≥ Fintype.card V := by
  sorry

end Konigsberg.Literature.Coloring.CranstonRabern_BrooksAndBeyond
