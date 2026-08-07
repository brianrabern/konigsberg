/-
HajnalLemma — stated.

For a collection 𝒬 of maximum cliques: |⋃𝒬| + |⋂𝒬| ≥ 2ω(G).
-/
import Konigsberg.Areas.Coloring.CliqueCollection
import Mathlib.Data.Set.Card

namespace Konigsberg.Literature.Coloring.HajnalLemma

open Set SimpleGraph Konigsberg.Areas.Coloring

variable {V : Type*} (G : SimpleGraph V)
variable [Fintype V] [DecidableEq V] [DecidableRel G.Adj]

/-- **HajnalLemma** (book \\label{HajnalLemma}). -/
theorem hajnalLemma (𝒬 : Set (Finset V))
    (hQ : 𝒬 ⊆ maxCliqueCollection G) :
    (⋃ Q ∈ 𝒬, (Q : Set V)).ncard + (⋂ Q ∈ 𝒬, (Q : Set V)).ncard ≥
      2 * G.cliqueNum := by
  sorry

end Konigsberg.Literature.Coloring.HajnalLemma
