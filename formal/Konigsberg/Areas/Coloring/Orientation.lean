/-
Areas/Coloring — orientations (scaffolding for SecondListBound / Kernel Magic / AT).

An orientation of `G` directs each edge; out-degree `d⁺` and acyclicity
(well-foundedness of the reverse-arc relation) are the ingredients of the
greedy-with-a-sink list-coloring bound (*Basic Graph Coloring*, SecondListBound).
-/
import Mathlib.Combinatorics.SimpleGraph.Finite
import Mathlib.Order.WellFounded
import Konigsberg.Areas.Coloring.Basic

namespace Konigsberg.Areas.Coloring

open Finset Function SimpleGraph

variable {V : Type*} (G : SimpleGraph V)

/-- An orientation of `G`: each undirected edge is given exactly one direction. -/
structure Orientation where
  /-- Directed adjacency: `Adj u v` means an arc `u → v`. -/
  Adj : V → V → Prop
  /-- Every arc lies over an edge of `G`. -/
  adj_of_edge : ∀ ⦃u v⦄, Adj u v → G.Adj u v
  /-- Each edge of `G` is oriented in exactly one direction. -/
  edge_oriented : ∀ ⦃u v⦄, G.Adj u v → Xor (Adj u v) (Adj v u)

namespace Orientation

variable {G}
variable (o : Orientation G)

lemma not_adj_symm {u v : V} (h : o.Adj u v) : ¬ o.Adj v u := by
  rcases o.edge_oriented (o.adj_of_edge h) with ⟨_, hnv⟩ | ⟨_, hnu⟩
  · exact hnv
  · exact absurd h hnu

/-- Out-neighbour set of `v` under the orientation. -/
def outNeighborSet (v : V) : Set V := {w | o.Adj v w}

/-- The orientation is acyclic: the reverse-arc relation is well-founded
(equivalently: every nonempty set of vertices has a sink). -/
def IsAcyclic : Prop := WellFounded fun a b => o.Adj b a

/-- Every nonempty set of vertices has a sink under an acyclic orientation. -/
theorem exists_sink (h : o.IsAcyclic) (s : Finset V) (hs : s.Nonempty) :
    ∃ a ∈ s, ∀ b ∈ s, ¬ o.Adj a b := by
  obtain ⟨a, ha, hmin⟩ := h.has_min (s : Set V) (by simpa using hs)
  exact ⟨a, ha, fun b hb => hmin b hb⟩

section Decidable
variable [DecidableRel o.Adj]

/-- Out-neighbour finset of `v`. -/
def outNeighborFinset [Fintype V] (v : V) : Finset V :=
  univ.filter (fun w => o.Adj v w)

lemma mem_outNeighborFinset [Fintype V] {v w : V} :
    w ∈ o.outNeighborFinset v ↔ o.Adj v w := by
  simp [outNeighborFinset]

/-- Out-degree `d⁺(v)`. -/
def outDegree [Fintype V] (v : V) : ℕ := #(o.outNeighborFinset v)

lemma outDegree_le_degree [Fintype V] [DecidableRel G.Adj] (v : V) :
    o.outDegree v ≤ G.degree v := by
  classical
  refine card_le_card ?_
  intro w hw
  exact (mem_neighborFinset _ _ _).mpr (o.adj_of_edge ((mem_outNeighborFinset o).mp hw))

/-- Out-degree of `v` counted only inside a vertex set `u`. -/
def outDegreeIn (u : Finset V) (v : V) : ℕ :=
  #(u.filter (fun w => o.Adj v w))

lemma outDegreeIn_univ [Fintype V] (v : V) :
    o.outDegreeIn univ v = o.outDegree v := by
  simp [outDegreeIn, outDegree, outNeighborFinset]

lemma outDegreeIn_le_outDegree [Fintype V] (u : Finset V) (v : V) :
    o.outDegreeIn u v ≤ o.outDegree v := by
  classical
  refine card_le_card ?_
  intro w hw
  exact (mem_outNeighborFinset o).mpr (mem_filter.mp hw).2

lemma outDegreeIn_sink {u : Finset V} {a : V}
    (hsink : ∀ b ∈ u, ¬ o.Adj a b) : o.outDegreeIn u a = 0 := by
  simp [outDegreeIn, filter_eq_empty_iff]
  exact fun b hb => hsink b hb

lemma outDegreeIn_erase_of_out [DecidableEq V] {u : Finset V} {a v : V} (ha : a ∈ u)
    (hout : o.Adj v a) :
    o.outDegreeIn (u.erase a) v = o.outDegreeIn u v - 1 := by
  classical
  have hmem : a ∈ u.filter (fun w => o.Adj v w) := mem_filter.mpr ⟨ha, hout⟩
  have hset :
      (u.erase a).filter (fun w => o.Adj v w) =
        (u.filter (fun w => o.Adj v w)).erase a := by
    ext w; simp [mem_filter, mem_erase, and_assoc]
  simpa [outDegreeIn, hset] using card_erase_of_mem hmem

lemma outDegreeIn_erase_of_not_out [DecidableEq V] {u : Finset V} {a v : V}
    (hnot : ¬ o.Adj v a) :
    o.outDegreeIn (u.erase a) v = o.outDegreeIn u v := by
  classical
  have hset :
      (u.erase a).filter (fun w => o.Adj v w) =
        u.filter (fun w => o.Adj v w) := by
    ext w
    simp only [mem_filter, mem_erase, and_assoc]
    constructor
    · exact fun ⟨hne, hw, hadj⟩ => ⟨hw, hadj⟩
    · intro ⟨hw, hadj⟩
      exact ⟨fun h => hnot (h ▸ hadj), hw, hadj⟩
  simp [outDegreeIn, hset]

end Decidable

end Orientation

/-! ### SecondListBound core (Areas-level) -/

/-- Acyclic orientation + `|L(v)| > d⁺(v)` ⇒ `G` is `L`-colorable.

Proof: on each remaining set `u`, colour a sink first. Induct on `u`, paint a
sink of `u`, shrink in-neighbour lists by that colour, apply IH to `u.erase a`. -/
theorem listColorable_of_acyclic_orientation [Fintype V] [DecidableEq V]
    (o : Orientation G) [DecidableRel o.Adj] (hacyc : o.IsAcyclic)
    (L : ListAssignment V) (hL : ∀ v, o.outDegree v < (L v).card) :
    ListColorable G L := by
  classical
  have aux : ∀ (u : Finset V) (L : ListAssignment V),
      (∀ v ∈ u, o.outDegreeIn u v < (L v).card) →
      ∃ c : V → ℕ, (∀ v ∈ u, c v ∈ L v) ∧
        (∀ p ∈ u, ∀ q ∈ u, G.Adj p q → c p ≠ c q) := by
    intro u
    induction u using Finset.strongInduction with
    | H u ih =>
      intro L hLu
      by_cases hu : u = ∅
      · subst hu; exact ⟨fun _ => 0, by simp, by simp⟩
      · obtain ⟨a, ha, hsink⟩ :=
          o.exists_sink hacyc u (nonempty_iff_ne_empty.mpr hu)
        have hpos : 0 < (L a).card := by
          have := hLu a ha
          have := o.outDegreeIn_sink hsink
          omega
        obtain ⟨x, hx⟩ := card_pos.mp hpos
        let L' : ListAssignment V := fun v =>
          if o.Adj v a then (L v).erase x else L v
        have hL' : ∀ v ∈ u.erase a, o.outDegreeIn (u.erase a) v < (L' v).card := by
          intro v hv
          have hv_u : v ∈ u := mem_of_mem_erase hv
          have hstrict : o.outDegreeIn u v < (L v).card := hLu v hv_u
          by_cases hout : o.Adj v a
          · have hdeg' : o.outDegreeIn (u.erase a) v = o.outDegreeIn u v - 1 :=
              o.outDegreeIn_erase_of_out ha hout
            have hpos_deg : 0 < o.outDegreeIn u v :=
              card_pos.mpr ⟨a, mem_filter.mpr ⟨ha, hout⟩⟩
            simp only [L', if_pos hout]
            by_cases hxL : x ∈ L v
            · have : ((L v).erase x).card = (L v).card - 1 := card_erase_of_mem hxL
              omega
            · have : ((L v).erase x).card = (L v).card := by
                simp [erase_eq_of_notMem hxL]
              omega
          · have hdeg' : o.outDegreeIn (u.erase a) v = o.outDegreeIn u v :=
              o.outDegreeIn_erase_of_not_out hout
            simp only [L', if_neg hout]
            omega
        obtain ⟨c, hc_mem, hc_proper⟩ :=
          ih (u.erase a) (erase_ssubset ha) L' hL'
        refine ⟨update c a x, ?_, ?_⟩
        · intro v hv
          by_cases hva : v = a
          · subst hva; rwa [update_self]
          · have hv' : v ∈ u.erase a := mem_erase.mpr ⟨hva, hv⟩
            rw [update_of_ne hva]
            have hcv := hc_mem v hv'
            simp only [L'] at hcv
            split_ifs at hcv with hadj
            · exact mem_of_mem_erase hcv
            · exact hcv
        · intro p hp q hq hpq
          if hpa : p = a then
            if hqa : q = a then
              rw [hpa, hqa] at hpq
              exact absurd hpq (G.loopless.irrefl _)
            else
              rw [hpa, update_self, update_of_ne hqa]
              have hq' : q ∈ u.erase a := mem_erase.mpr ⟨hqa, hq⟩
              intro hc_eq
              rcases o.edge_oriented (hpa ▸ hpq) with ⟨hout, _⟩ | ⟨hin, _⟩
              · exact hsink q hq hout
              · have hc_mem' := hc_mem q hq'
                simp only [L', if_pos hin] at hc_mem'
                exact (ne_of_mem_erase hc_mem').symm hc_eq
          else if hqa : q = a then
            rw [hqa, update_of_ne hpa, update_self]
            have hp' : p ∈ u.erase a := mem_erase.mpr ⟨hpa, hp⟩
            intro hc_eq
            rcases o.edge_oriented (hqa ▸ hpq) with ⟨hout, _⟩ | ⟨hin, _⟩
            · have hc_mem' := hc_mem p hp'
              simp only [L', if_pos hout] at hc_mem'
              exact ne_of_mem_erase hc_mem' hc_eq
            · exact hsink p hp hin
          else
            rw [update_of_ne hpa, update_of_ne hqa]
            exact hc_proper p (mem_erase.mpr ⟨hpa, hp⟩) q
              (mem_erase.mpr ⟨hqa, hq⟩) hpq
  obtain ⟨c, hmem, hproper⟩ := aux univ L (fun v _ => by
    rw [o.outDegreeIn_univ]; exact hL v)
  exact ⟨c, fun v => hmem v (mem_univ v),
    fun u v huv => hproper u (mem_univ u) v (mem_univ v) huv⟩

/-- Acyclic orientation ⇒ `G` is pointwise `(d⁺+1)`-choosable. -/
theorem fChoosable_outDegree_succ [Fintype V] [DecidableEq V]
    (o : Orientation G) [DecidableRel o.Adj] (hacyc : o.IsAcyclic) :
    FChoosable G (fun v => o.outDegree v + 1) := by
  intro L hL
  exact listColorable_of_acyclic_orientation G o hacyc L fun v => Nat.lt_of_succ_le (hL v)

end Konigsberg.Areas.Coloring
