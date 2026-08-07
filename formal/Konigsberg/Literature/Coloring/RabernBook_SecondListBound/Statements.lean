/-
SecondListBound — Rabern, *Basic Graph Coloring*, §"Coloring with prescribed list sizes".

If `G` admits an acyclic orientation with `|L(v)| > d⁺(v)` for all `v`
(equivalently `|L(v)| ≥ d⁺(v)+1`), then `G` is `L`-colorable.
-/
import Konigsberg.Areas.Coloring.Orientation

namespace Konigsberg.Literature.Coloring.RabernBook_SecondListBound

open SimpleGraph
open Konigsberg.Areas.Coloring

variable {V : Type*} (G : SimpleGraph V)

/-- If `|L(v)| ≥ d⁺(v)+1` under an acyclic orientation, then `G` is `L`-colorable.
Greedy-with-a-sink: colour a sink of the remaining set first; shrink in-neighbour
lists and induct. Proved as `fChoosable_outDegree_succ` in `Areas.Coloring.Orientation`. -/
theorem secondListBound [Fintype V] [DecidableEq V]
    (o : Orientation G) [DecidableRel o.Adj] (hacyc : o.IsAcyclic) :
    FChoosable G (fun v => o.outDegree v + 1) :=
  fChoosable_outDegree_succ G o hacyc

end Konigsberg.Literature.Coloring.RabernBook_SecondListBound
