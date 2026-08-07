/-
EulerianOrientationsLemma — stated.

For an orientation `o`, `||EE| − |EO|| = |p_{d⁺}(G)|`.
This is the formal target corresponding to empirical AT certificates
(`sign_sum` / `graph_polynomial_coefficient`).
-/
import Konigsberg.Areas.Coloring.GraphPolynomial

namespace Konigsberg.Literature.Coloring.EulerianOrientationsLemma

open Konigsberg.Areas.Coloring

variable {V : Type*} (G : SimpleGraph V)
variable [Fintype V] [DecidableEq V] [LinearOrder V] [DecidableRel G.Adj]

/-- **EulerianOrientationsLemma** (book env `EulerianOrientationsLemma`).

`|EE(o) − EO(o)| = |p_{d⁺(o)}(G)|`. -/
theorem eulerianOrientationsLemma (o : Orientation G) [DecidableRel o.Adj] :
    Int.natAbs (eulerianSignDiff G o) =
      Int.natAbs (graphPolynomialCoeff G o.outDegree) := by
  sorry

end Konigsberg.Literature.Coloring.EulerianOrientationsLemma
