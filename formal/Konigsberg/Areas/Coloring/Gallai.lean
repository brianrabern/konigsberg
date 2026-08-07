/-
Areas/Coloring — Gallai trees (blocks = complete or odd cycle).

Source scaffolding for Brooks' theorem for list coloring (book § stub under
Kernel magic). A connected graph is a Gallai tree when every block is a
complete graph or an odd cycle (Erdős–Rubin–Taylor).
-/
import Mathlib.Combinatorics.SimpleGraph.Circulant
import Mathlib.Combinatorics.SimpleGraph.Clique
import Mathlib.Combinatorics.SimpleGraph.Connectivity.Connected
import Mathlib.Combinatorics.SimpleGraph.Finite
namespace Konigsberg.Areas.Coloring

open SimpleGraph

variable {V : Type*} (G : SimpleGraph V)

/-- Bridgeless: no edge is a bridge. -/
def IsBridgeless : Prop :=
  ∀ ⦃e : Sym2 V⦄, e ∈ G.edgeSet → ¬ G.IsBridge e

/-- `B` is a *block* of `G`: either the two endpoints of a bridge, or a maximal
nonempty vertex set inducing a connected bridgeless subgraph. -/
def IsBlock (B : Set V) : Prop :=
  (∃ u v, G.IsBridge s(u, v) ∧ B = {u, v}) ∨
    (B.Nonempty ∧ (G.induce B).Connected ∧ IsBridgeless (G.induce B) ∧
      ∀ B' : Set V, B ⊆ B' → (G.induce B').Connected → IsBridgeless (G.induce B') →
        B' = B)

/-- Induced subgraph on `B` is isomorphic to an odd cycle. -/
def IsOddCycleBlock (B : Set V) : Prop :=
  ∃ n : ℕ, Odd n ∧ Nonempty ((G.induce B) ≃g cycleGraph n)

/-- Gallai tree: connected, and every block is a clique or an odd cycle. -/
def IsGallaiTree : Prop :=
  G.Connected ∧ ∀ ⦃B : Set V⦄, IsBlock G B → G.IsClique B ∨ IsOddCycleBlock G B

end Konigsberg.Areas.Coloring
