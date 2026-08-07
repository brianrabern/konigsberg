/-
KostochkaYanceyKernelLemma — stated.

If G is a superoriented graph with an independent set I such that all edges in
G−I have back arrows (both directions), then G is kernel-perfect.
-/
import Konigsberg.Areas.Coloring.Kernel

namespace Konigsberg.Literature.Coloring.KostochkaYanceyKernelLemma

open Konigsberg.Areas.Coloring

variable {V : Type*} (G : SimpleGraph V)

/-- All edges of the induced subgraph on `S` are bidirected under `s`. -/
def HasBackArrows (s : Superorientation G) (S : Set V) : Prop :=
  ∀ ⦃u v⦄, u ∈ S → v ∈ S → G.Adj u v → s.Adj u v ∧ s.Adj v u

/-- **KostochkaYanceyKernelLemma** (book \label{KostochkaYanceyKernelLemma}). -/
theorem kostochkaYanceyKernelLemma (s : Superorientation G) (I : Set V)
    (hI : G.IsIndepSet I)
    (hback : HasBackArrows G s (Set.univ \ I)) :
    s.KernelPerfect := by
  sorry

end Konigsberg.Literature.Coloring.KostochkaYanceyKernelLemma
