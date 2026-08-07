/-
KiersteadRabern_OreVizing — edge lower bounds + Ore–Brooks for list coloring.

Source: `github.com/landon/Research/OreVizing` (arXiv:1406.7355).
Public domain. Statements typecheck; proofs deferred (`status = "stated"`).
-/
import Mathlib.Combinatorics.SimpleGraph.Clique
import Mathlib.Combinatorics.SimpleGraph.Maps
import Mathlib.Data.Rat.Defs
import Konigsberg.Areas.Coloring.Basic
import Konigsberg.Literature.Coloring.Rabern_4ListCriticalEdgeBound.Statements

namespace Konigsberg.Literature.Coloring.KiersteadRabern_OreVizing

open Finset SimpleGraph
open Konigsberg.Areas.Coloring
open Konigsberg.Literature.Coloring.Rabern_4ListCriticalEdgeBound
  (NotCompleteOfOrder)

variable {V : Type*} (G : SimpleGraph V)
variable [Fintype V] [DecidableEq V] [DecidableRel G.Adj]

/-! ### Gallai-style bound function `g_k(n,c)` -/

/-- `α_k = 1/2 − 1/((k−1)(k−2))` (Kostochka–Stiebitz / Kierstead–Rabern). -/
noncomputable def alpha (k : ℕ) : ℚ :=
  (1 : ℚ) / 2 - 1 / (((k - 1) * (k - 2) : ℕ) : ℚ)

/-- `g_k(n,c) = (k−1 + (k−3)/((k−c)(k−1)+k−3)) · n`. -/
noncomputable def gallaiBound (k n : ℕ) (c : ℚ) : ℚ :=
  let D : ℚ := ((k : ℚ) - c) * (k - 1) + (k - 3)
  ((k - 1 : ℚ) + (k - 3 : ℚ) / D) * n

/-- Parameter `c` in the Main Edge Bound: `(k−3)α_k` for `k ≥ 8`, else
`(k−4)α_k` for `k ∈ {6,7}`. -/
noncomputable def edgeBoundC (k : ℕ) : ℚ :=
  if 8 ≤ k then (k - 3 : ℚ) * alpha k else (k - 4 : ℚ) * alpha k

/-! ### Main edge bound (list-critical) -/

/-- **EdgeBound** (Kierstead–Rabern, arXiv:1406.7355 Thm.).

For `k ≥ 6` and `G ≠ K_k` a `k`-list-critical graph,
`2‖G‖ ≥ g_k(|G|, c)` with `c = (k−3)α_k` (`k ≥ 8`) or `(k−4)α_k`
(`k ∈ {6,7}`). -/
theorem edgeBound_listCritical {k : ℕ} (hk : 6 ≤ k)
    (hcrit : KListCritical G k) (hne : NotCompleteOfOrder G k) :
    (2 * G.edgeFinset.card : ℚ) ≥ gallaiBound k (Fintype.card V) (edgeBoundC k) := by
  sorry

/-! ### Ore degree + Ore–Brooks for list coloring -/

/-- Ore-degree of `G`: `θ(G) = max_{uv ∈ E} (deg(u) + deg(v))`. -/
noncomputable def oreDegree : ℕ :=
  sSup {G.degree u + G.degree v | (u : V) (v : V) (_ : G.Adj u v)}

/-- **OurListOre** — Ore-degree Brooks for list coloring:
`θ ≥ 18` and `ω ≤ θ/2` ⇒ `⌊θ/2⌋`-choosable. -/
theorem oreBrooks_list (hθ : 18 ≤ oreDegree G)
    (hω : 2 * G.cliqueNum ≤ oreDegree G) :
    Choosable G (oreDegree G / 2) := by
  sorry

end Konigsberg.Literature.Coloring.KiersteadRabern_OreVizing
