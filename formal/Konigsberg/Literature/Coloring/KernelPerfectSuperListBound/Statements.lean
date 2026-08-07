/-
KernelPerfectSuperListBound — stated. Same bound for kernel-perfect superorientations.
-/
import Konigsberg.Areas.Coloring.Kernel

namespace Konigsberg.Literature.Coloring.KernelPerfectSuperListBound

open Konigsberg.Areas.Coloring

variable {V : Type*} (G : SimpleGraph V)
variable [Fintype V] [DecidableEq V] [DecidableRel G.Adj]

/-- **KernelPerfectSuperListBound** (book \label{KernelPerfectSuperListBound}). -/
theorem kernelPerfectSuperListBound (s : Superorientation G) [DecidableRel s.Adj]
    (hperf : s.KernelPerfect) (L : ListAssignment V)
    (hL : ∀ v, s.outDegree v < (L v).card) :
    ListColorable G L := by
  sorry

end Konigsberg.Literature.Coloring.KernelPerfectSuperListBound
