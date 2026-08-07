/-
Areas/Coloring — graph polynomial scaffolding for Combinatorial Nullstellensatz / AT.

Source: *Basic Graph Coloring* ch. Combinatorial nullstellensatz, §The graph
polynomial. Definitions are shaped to match the empirical
`graph_polynomial_coefficient` / `sign_sum` bridge (`alon_tarsi.py`).
-/
import Mathlib.Algebra.MvPolynomial.Basic
import Mathlib.Combinatorics.SimpleGraph.Finite
import Konigsberg.Areas.Coloring.Orientation

namespace Konigsberg.Areas.Coloring

open Finset MvPolynomial SimpleGraph

variable {V : Type*} (G : SimpleGraph V)

/-- Graph polynomial `p_G = ∏_{{u,v}∈E, u<v} (X_u − X_v)` over `ℤ`.
Requires a linear order so each undirected edge contributes one ordered factor. -/
noncomputable def graphPolynomial [Fintype V] [DecidableEq V] [LinearOrder V]
    [DecidableRel G.Adj] : MvPolynomial V ℤ :=
  ∏ e ∈ G.edgeFinset,
    let p := (e : Sym2 V).out
    let u := min p.1 p.2
    let v := max p.1 p.2
    (X u - X v : MvPolynomial V ℤ)

/-- Coefficient `p_k(G)` of `∏_v X_v^{k v}` in `p_G`. -/
noncomputable def graphPolynomialCoeff [Fintype V] [DecidableEq V] [LinearOrder V]
    [DecidableRel G.Adj] (k : V → ℕ) : ℤ :=
  coeff (Finsupp.equivFunOnFinite.symm k) (graphPolynomial G)

/-- Spanning Eulerian subdigraphs of an orientation with even / odd edge count.
Defined as cardinalities of the corresponding arc-subsets (in-degree = out-degree
at every vertex). -/
noncomputable def eeCount [Fintype V] [DecidableEq V] [DecidableRel G.Adj]
    (o : Orientation G) [DecidableRel o.Adj] : ℕ :=
  let arcs : Finset (V × V) :=
    (univ.product univ).filter fun p => o.Adj p.1 p.2
  #{S ∈ arcs.powerset |
      (∀ v, #{a ∈ S | a.1 = v} = #{a ∈ S | a.2 = v}) ∧ Even S.card}

noncomputable def eoCount [Fintype V] [DecidableEq V] [DecidableRel G.Adj]
    (o : Orientation G) [DecidableRel o.Adj] : ℕ :=
  let arcs : Finset (V × V) :=
    (univ.product univ).filter fun p => o.Adj p.1 p.2
  #{S ∈ arcs.powerset |
      (∀ v, #{a ∈ S | a.1 = v} = #{a ∈ S | a.2 = v}) ∧ Odd S.card}

/-- Signed Eulerian difference `|EE| − |EO|` (empirical `sign_sum` target). -/
noncomputable def eulerianSignDiff [Fintype V] [DecidableEq V] [DecidableRel G.Adj]
    (o : Orientation G) [DecidableRel o.Adj] : ℤ :=
  (eeCount G o : ℤ) - (eoCount G o : ℤ)

end Konigsberg.Areas.Coloring
