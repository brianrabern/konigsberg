/-
KernelPerfectListBound — stated.

If L is a list assignment on a kernel-perfect oriented graph G with
|L(v)| > d⁺(v) for all v, then G is L-colorable.
-/
import Konigsberg.Areas.Coloring.Kernel

namespace Konigsberg.Literature.Coloring.KernelPerfectListBound

open Konigsberg.Areas.Coloring

variable {V : Type*} (G : SimpleGraph V)
variable [Fintype V] [DecidableEq V] [DecidableRel G.Adj]

/-- **KernelPerfectListBound** (book \label{KernelPerfectListBound}). -/
theorem kernelPerfectListBound (o : Orientation G) [DecidableRel o.Adj]
    (hperf : o.KernelPerfect) (L : ListAssignment V)
    (hL : ∀ v, o.outDegree v < (L v).card) :
    ListColorable G L := by
  sorry

end Konigsberg.Literature.Coloring.KernelPerfectListBound
