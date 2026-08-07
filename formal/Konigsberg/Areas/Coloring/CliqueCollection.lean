/-
Areas/Coloring — max-clique collection and clique-intersection graph.

Source: *Basic Graph Coloring* / `gct.tex` §hitting all maximum cliques
(`X_𝒬`). Uses mathlib `cliqueNum` / `IsNClique` / `maxDegree`.
-/
import Mathlib.Combinatorics.SimpleGraph.Clique
import Mathlib.Combinatorics.SimpleGraph.Finite

namespace Konigsberg.Areas.Coloring

open Finset SimpleGraph

variable {V : Type*} (G : SimpleGraph V)

/-- The collection `𝒬` of all maximum cliques (as finsets), when `V` is finite. -/
noncomputable def maxCliqueCollection [Fintype V] [DecidableEq V] [DecidableRel G.Adj] :
    Set (Finset V) :=
  {Q | G.IsNClique G.cliqueNum Q}

/-- Intersection graph `X_𝒬`: vertices are the members of `𝒬`, adjacent when
they intersect and are distinct. -/
def cliqueIntersectionGraph [DecidableEq V] (𝒬 : Set (Finset V)) : SimpleGraph 𝒬 where
  Adj Q₁ Q₂ := Q₁ ≠ Q₂ ∧ ((Q₁ : Finset V) ∩ (Q₂ : Finset V)).Nonempty
  symm := by
    refine ⟨fun Q₁ Q₂ ⟨hne, h⟩ => ?_⟩
    exact ⟨hne.symm, by simpa [Finset.inter_comm] using h⟩
  loopless := by
    refine ⟨fun Q h => ?_⟩
    exact h.1 rfl

/-- Convenience: `X_𝒬` for the full max-clique collection. -/
noncomputable def maxCliqueIntersectionGraph
    [Fintype V] [DecidableEq V] [DecidableRel G.Adj] :
    SimpleGraph ↑(maxCliqueCollection G) :=
  cliqueIntersectionGraph (maxCliqueCollection G)

end Konigsberg.Areas.Coloring
