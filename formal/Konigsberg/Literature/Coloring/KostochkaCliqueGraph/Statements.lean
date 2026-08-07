/-
KostochkaCliqueGraph — stated.

ω(G) > (2/3)(Δ+1) and X_𝒬 connected ⇒ ⋂𝒬 ≠ ∅.
-/
import Konigsberg.Areas.Coloring.CliqueCollection
import Mathlib.Combinatorics.SimpleGraph.Connectivity.Connected

namespace Konigsberg.Literature.Coloring.KostochkaCliqueGraph

open Finset SimpleGraph Konigsberg.Areas.Coloring

variable {V : Type*} (G : SimpleGraph V)
variable [Fintype V] [DecidableEq V] [DecidableRel G.Adj]

/-- **KostochkaCliqueGraph** (book \\label{KostochkaCliqueGraph}). -/
theorem kostochkaCliqueGraph (𝒬 : Set (Finset V))
    (hQ : 𝒬 ⊆ maxCliqueCollection G)
    (hω : (2 * G.maxDegree + 2 : ℕ) < 3 * G.cliqueNum)
    (hconn : (cliqueIntersectionGraph 𝒬).Connected) :
    (⋂ Q ∈ 𝒬, (Q : Set V)).Nonempty := by
  sorry

end Konigsberg.Literature.Coloring.KostochkaCliqueGraph
