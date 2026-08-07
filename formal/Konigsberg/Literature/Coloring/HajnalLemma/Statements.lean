/-
HajnalLemma — stated.

For a nonempty collection 𝒬 of maximum cliques: |⋃𝒬| + |⋂𝒬| ≥ 2ω(G).
-/
import Konigsberg.Areas.Coloring.CliqueCollection
import Mathlib.Data.Set.Card

namespace Konigsberg.Literature.Coloring.HajnalLemma

open Set SimpleGraph Konigsberg.Areas.Coloring

variable {V : Type*} (G : SimpleGraph V)
variable [Fintype V] [DecidableEq V] [DecidableRel G.Adj]

/-- **HajnalLemma** (book \\label{HajnalLemma}).

Requires `𝒬.Nonempty`: with `𝒬 = ∅`, Lean’s `⋂ Q ∈ ∅` is `univ`, and the
claim becomes `0 + |V| ≥ 2ω`, which fails for `K_n` (`n ≥ 2`). -/
theorem hajnalLemma (𝒬 : Set (Finset V))
    (hne : 𝒬.Nonempty)
    (hQ : 𝒬 ⊆ maxCliqueCollection G) :
    (⋃ Q ∈ 𝒬, (Q : Set V)).ncard + (⋂ Q ∈ 𝒬, (Q : Set V)).ncard ≥
      2 * G.cliqueNum := by
  sorry

end Konigsberg.Literature.Coloring.HajnalLemma
