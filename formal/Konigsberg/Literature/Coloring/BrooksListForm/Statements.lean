/-
BrooksListForm — stated (list Brooks / Gallai-tree characterization).

Book section is a stub; we state the standard Erdős–Rubin–Taylor form:
a connected graph is degree-choosable iff it is not a Gallai tree.
Cross-ref: EXTERNAL BrooksLean is ordinary (chromatic) Brooks.
-/
import Konigsberg.Areas.Coloring.Gallai
import Konigsberg.Areas.Coloring.Basic

namespace Konigsberg.Literature.Coloring.BrooksListForm

open Konigsberg.Areas.Coloring

variable {V : Type*} (G : SimpleGraph V)
variable [Fintype V] [DecidableEq V] [DecidableRel G.Adj]

/-- **BrooksListForm** — list-coloring Brooks via Gallai trees.
Connected `G` is degree-choosable ↔ `G` is not a Gallai tree. -/
theorem brooksListForm (hconn : G.Connected) :
    DegreeChoosable G ↔ ¬ IsGallaiTree G := by
  sorry

end Konigsberg.Literature.Coloring.BrooksListForm
