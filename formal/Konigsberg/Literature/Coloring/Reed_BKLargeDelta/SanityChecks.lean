/-
SanityChecks for Reed_BKLargeDelta — the theorem is CITED (sorry), so these only
witness that the statement is meaningful, not that Reed's proof is here.
`Colorable` is not `Decidable`, so no `decide`; use `colorable_of_fintype`.
-/
import Mathlib.Combinatorics.SimpleGraph.Clique
import Konigsberg.Areas.Coloring.Basic

namespace Konigsberg.Literature.Coloring.Reed_BKLargeDelta

open SimpleGraph

/-- Minimal existence probe: the `ω < Δ` regime is inhabited — the star `K_{1,3}`
(= `completeBipartiteGraph`) has Δ = 3, ω = 2. It is (trivially) colorable, so the
conclusion class is non-empty. (A tighter probe would show it is `2 = Δ−1`-colorable;
left as a TODO — this only witnesses non-vacuity.) -/
example : (completeBipartiteGraph (Fin 1) (Fin 3)).Colorable
    (Fintype.card (Fin 1 ⊕ Fin 3)) :=
  colorable_of_fintype _

end Konigsberg.Literature.Coloring.Reed_BKLargeDelta
