/-
Areas/Coloring — kernels and kernel-perfect (super)orientations.

Source: *Basic Graph Coloring*, defs preceding `\label{KernelPerfectListBound}`.
A kernel is an independent out-dominating set; kernel-perfect means every
vertex subset admits a kernel in the restricted digraph. Superorientations
allow digons. Enough to *state* KernelPerfect* theorems; proofs deferred.
-/
import Mathlib.Combinatorics.SimpleGraph.Finite
import Konigsberg.Areas.Coloring.Orientation

namespace Konigsberg.Areas.Coloring

open Set SimpleGraph

variable {V : Type*} {G : SimpleGraph V}

/-! ### Kernels in an orientation -/

/-- A *kernel* in an oriented graph: independent `I` such that every vertex
outside `I` has an out-neighbour in `I`. -/
def Orientation.IsKernel (o : Orientation G) (I : Set V) : Prop :=
  G.IsIndepSet I ∧ ∀ ⦃v⦄, v ∉ I → ∃ u ∈ I, o.Adj v u

/-- Kernel-perfect orientation: every `S ⊆ V` admits a kernel using only arcs
inside `S`. -/
def Orientation.KernelPerfect (o : Orientation G) : Prop :=
  ∀ S : Set V, ∃ I ⊆ S,
    G.IsIndepSet I ∧ (∀ ⦃v⦄, v ∈ S → v ∉ I → ∃ u ∈ I, u ∈ S ∧ o.Adj v u)

/-! ### Superorientations (digons allowed) -/

/-- A *superorientation* of `G`: each undirected edge gets ≥1 direction;
both directions (a digon) are allowed. -/
structure Superorientation (G : SimpleGraph V) where
  Adj : V → V → Prop
  adj_of_edge : ∀ ⦃u v⦄, Adj u v → G.Adj u v
  covers : ∀ ⦃u v⦄, G.Adj u v → Adj u v ∨ Adj v u

namespace Superorientation

variable (s : Superorientation G)

/-- Kernel in a superoriented digraph. -/
def IsKernel (I : Set V) : Prop :=
  G.IsIndepSet I ∧ ∀ ⦃v⦄, v ∉ I → ∃ u ∈ I, s.Adj v u

/-- Kernel-perfect superorientation. -/
def KernelPerfect : Prop :=
  ∀ S : Set V, ∃ I ⊆ S,
    G.IsIndepSet I ∧ (∀ ⦃v⦄, v ∈ S → v ∉ I → ∃ u ∈ I, u ∈ S ∧ s.Adj v u)

/-- Out-degree under a superorientation. -/
noncomputable def outDegree [Fintype V] [DecidableRel s.Adj] (v : V) : ℕ :=
  Fintype.card {w // s.Adj v w}

end Superorientation

end Konigsberg.Areas.Coloring
