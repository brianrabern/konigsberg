/-
Reed_BKLargeDelta — Borodin–Kostochka holds for large maximum degree (CITED).

Reed (1999): there is a constant `Δ₀` such that every graph with `Δ ≥ Δ₀` and
`ω < Δ` satisfies `χ ≤ Δ − 1` (i.e. BK holds for all sufficiently large Δ). The
constant has since been made explicit and constructive (`Δ ≥ 5.2·10⁹`,
arXiv:2603.16670).

⚠️ CITED, NOT FORMALIZED. This statement is `stated` with `sorry` on purpose: it
records a known external theorem so the campaign knows the large-Δ regime is
already settled and can focus on the live regime **Δ = 9**. It is a *frame*, not a
target — do NOT try to prove it, and do NOT promote it to `formalized` without an
actual formalization of Reed's proof (a major undertaking, out of scope). Any kernel
proof that cites this lemma inherits `sorryAx`, which the axiom gate and the campaign
settlement check both reject — so this frame cannot be silently laundered into a BK
"proof". Statement written blind against the corpus API; build to confirm it
elaborates (universe/instance binders inside `∃` may need adjustment).
-/
import Mathlib.Combinatorics.SimpleGraph.Clique
import Konigsberg.Areas.Coloring.Basic

namespace Konigsberg.Literature.Coloring.Reed_BKLargeDelta

open SimpleGraph

/-- **Reed's large-Δ Borodin–Kostochka.** There is a threshold `Δ₀` beyond which BK
holds: for every finite graph with `Δ ≥ Δ₀` and `ω < Δ`, `χ ≤ Δ − 1`. Cited
(Reed 1999); not formalized here. -/
theorem reed_bk_large_delta :
    ∃ Δ₀ : ℕ,
      ∀ {V : Type} [Fintype V] [DecidableEq V]
        (G : SimpleGraph V) [DecidableRel G.Adj],
        Δ₀ ≤ G.maxDegree → G.cliqueNum < G.maxDegree →
        G.Colorable (G.maxDegree - 1) := by
  sorry

end Konigsberg.Literature.Coloring.Reed_BKLargeDelta
