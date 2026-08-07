/-
DeltaEdgeColoring — stated.

If G is bipartite, then G is Δ(G)-edge-colorable
(equivalently: the line graph is Δ-colorable).
-/
import Mathlib.Combinatorics.SimpleGraph.Bipartite
import Mathlib.Combinatorics.SimpleGraph.LineGraph
import Mathlib.Combinatorics.SimpleGraph.Coloring.Vertex
import Mathlib.Combinatorics.SimpleGraph.Finite

namespace Konigsberg.Literature.Coloring.DeltaEdgeColoring

open SimpleGraph

variable {V : Type*} (G : SimpleGraph V)
variable [Fintype V] [DecidableEq V] [DecidableRel G.Adj]

/-- **DeltaEdgeColoring** (book \\label{DeltaEdgeColoring}).

Bipartite ⇒ line graph is `maxDegree`-colorable. -/
theorem deltaEdgeColoring (hb : G.IsBipartite) :
    G.lineGraph.Colorable G.maxDegree := by
  sorry

end Konigsberg.Literature.Coloring.DeltaEdgeColoring
