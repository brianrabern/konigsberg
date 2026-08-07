/-
Areas/Coloring — f-irreducibility (Rabern PRIMARY criticality).

Source: *Basic Graph Coloring* §"Coloring with prescribed list sizes"
(see docs/handoff/M2_FIRREDUCIBLE.md, COLORING_BOOK_ROADMAP.md).

This is the BK-adjacent notion: an `f`-numbering on `G`, restriction `f_H` to an
induced subgraph, and f-reducible / f-irreducible. `basicIrreducible` is the
seed of every list-critical edge lower bound (`f v ≤ d(v)` ⇒ `2|E| ≥ ∑ f`).

Deliberately separate from the classical edge/subgraph list-criticality in
`Basic.lean` — keep both; do not conflate them.
-/
import Mathlib.Algebra.BigOperators.Group.Finset.Basic
import Mathlib.Combinatorics.SimpleGraph.DegreeSum
import Konigsberg.Areas.Coloring.Basic

namespace Konigsberg.Areas.Coloring

open Finset Function SimpleGraph

variable {V : Type*} (G : SimpleGraph V)
variable [Fintype V] [DecidableEq V] [DecidableRel G.Adj]

/-! ### G-numberings and ℤ-valued choosability -/

/-- A G-numbering: `f : V → ℤ` with `f v ≤ deg(v) + 1` for all `v`.
Uses `ℤ` (not `ℕ`) so the induced restriction `f_H` can go ≤ 0. -/
def IsGNumbering (f : V → ℤ) : Prop :=
  ∀ v, f v ≤ (G.degree v : ℤ) + 1

/-- ℤ-valued `f`-choosability. When `f v ≤ 0`, the empty list is admissible at
`v`, so `FChoosableZ` correctly fails unless `V` is empty of such vertices. -/
def FChoosableZ (f : V → ℤ) : Prop :=
  ∀ L : ListAssignment V, (∀ v, f v ≤ ((L v).card : ℤ)) → ListColorable G L

/-- ℕ-valued and ℤ-valued choosability agree on nonnegative numberings. -/
theorem fChoosableZ_coe (g : V → ℕ) :
    FChoosableZ G (fun v => (g v : ℤ)) ↔ FChoosable G g := by
  constructor
  · intro h L hL
    exact h L fun v => Int.ofNat_le_ofNat_of_le (hL v)
  · intro h L hL
    exact h L fun v => Nat.cast_le.mp (hL v)

/-! ### Induced restriction `f_H` -/

/-- Restriction of a numbering to an induced subgraph on `s`:
`f_H(w) = f(w) − (d_G(w) − d_H(w))`, i.e. `f` minus the number of edges from
`w` leaving `s`. Mirrors the book's `f_H(v) = f(v) − |v, G−H|`. -/
noncomputable def fH (s : Set V) [DecidablePred (· ∈ s)] (f : V → ℤ) (w : s) : ℤ :=
  f (w : V) - ((G.degree (w : V) : ℤ) - ((G.induce s).degree w : ℤ))

/-! ### f-reducible / f-irreducible -/

/-- `G` is *f-reducible* if some nonempty induced subgraph is `f_H`-choosable.
The existential carries a `DecidablePred` instance so `induce`/`fH` typecheck
(quantifies over all nonempty subsets, including `univ`). -/
def FReducible (f : V → ℤ) : Prop :=
  ∃ (s : Set V) (_ : DecidablePred (· ∈ s)),
    s.Nonempty ∧ FChoosableZ (G.induce s) (fH G s f)

/-- `G` is *f-irreducible* if it is not f-reducible. -/
def FIrreducible (f : V → ℤ) : Prop := ¬ FReducible G f

/-! ### BasicIrreducible — seed of every edge bound -/

lemma degree_induce_singleton (v : V) :
    (G.induce ({v} : Set V)).degree ⟨v, Set.mem_singleton v⟩ = 0 := by
  classical
  rw [degree, Finset.card_eq_zero]
  refine Finset.eq_empty_iff_forall_notMem.mpr ?_
  intro w hw
  have hAdj : G.Adj ↑(⟨v, Set.mem_singleton v⟩ : ({v} : Set V)) ↑w := by
    simpa [mem_neighborFinset] using hw
  have hw' : ↑w = v := Set.eq_of_mem_singleton w.property
  rw [show ↑(⟨v, Set.mem_singleton v⟩ : ({v} : Set V)) = v from rfl, hw'] at hAdj
  exact (G.loopless.irrefl v) hAdj

lemma fH_singleton (f : V → ℤ) (v : V) :
    fH G ({v} : Set V) f ⟨v, Set.mem_singleton v⟩ = f v - (G.degree v : ℤ) := by
  simp only [fH]
  have h0 := degree_induce_singleton G v
  simp [h0]

lemma listColorable_singleton (v : V) (L : ListAssignment ({v} : Set V))
    (hL : 0 < (L ⟨v, Set.mem_singleton v⟩).card) :
    ListColorable (G.induce ({v} : Set V)) L := by
  classical
  obtain ⟨x, hx⟩ := Finset.card_pos.mp hL
  refine ⟨fun _ => x, fun w => ?_, ?_⟩
  · have hw : (w : V) = v := Set.eq_of_mem_singleton w.property
    have : w = ⟨v, Set.mem_singleton v⟩ := Subtype.ext hw
    rw [this]; exact hx
  · intro a b hab
    have ha : (a : V) = v := Set.eq_of_mem_singleton a.property
    have hb : (b : V) = v := Set.eq_of_mem_singleton b.property
    change G.Adj (a : V) (b : V) at hab
    rw [ha, hb] at hab
    exact absurd hab (G.loopless.irrefl v)

lemma fChoosableZ_singleton_of_pos (v : V) (f : ({v} : Set V) → ℤ)
    (hf : 1 ≤ f ⟨v, Set.mem_singleton v⟩) :
    FChoosableZ (G.induce ({v} : Set V)) f := by
  intro L hL
  have hleℤ : (1 : ℤ) ≤ (L ⟨v, Set.mem_singleton v⟩).card :=
    le_trans hf (hL _)
  have hpos : 0 < (L ⟨v, Set.mem_singleton v⟩).card := by
    exact_mod_cast (lt_of_lt_of_le (by decide : (0 : ℤ) < 1) hleℤ)
  exact listColorable_singleton G v L hpos

/-- If `G` is f-irreducible, then `f v ≤ deg(v)` for every vertex.
Proof: otherwise the singleton `{v}` is `f_H`-choosable (`f_H ≥ 1`), so `G` is
f-reducible. -/
theorem basicIrreducible (f : V → ℤ) (h : FIrreducible G f) :
    ∀ v, f v ≤ (G.degree v : ℤ) := by
  intro v
  by_contra hv
  replace hv : (G.degree v : ℤ) + 1 ≤ f v := by omega
  have hpos : 1 ≤ fH G ({v} : Set V) f ⟨v, Set.mem_singleton v⟩ := by
    rw [fH_singleton]; omega
  refine h ⟨({v} : Set V), inferInstance, Set.singleton_nonempty v,
    fChoosableZ_singleton_of_pos G v _ hpos⟩

/-- Handshaking corollary: f-irreducibility ⇒ `∑ f ≤ 2|E|`. -/
theorem sum_le_two_mul_card_edgeFinset (f : V → ℤ) (h : FIrreducible G f) :
    ∑ v, f v ≤ 2 * (G.edgeFinset.card : ℤ) := by
  have hf := basicIrreducible G f h
  calc
    ∑ v, f v ≤ ∑ v, (G.degree v : ℤ) := Finset.sum_le_sum fun i _ => hf i
    _ = ↑(∑ v, G.degree v) := by simp
    _ = ↑(2 * G.edgeFinset.card) := by rw [sum_degrees_eq_twice_card_edges]
    _ = 2 * (G.edgeFinset.card : ℤ) := by simp

end Konigsberg.Areas.Coloring
