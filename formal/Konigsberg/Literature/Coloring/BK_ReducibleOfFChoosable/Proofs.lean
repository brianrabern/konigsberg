/-
Proofs for BK_ReducibleOfFChoosable — the reducibility bridge.

Lemma 1 — induce-degree counts ambient neighbours inside `s`.
Lemma 2 — external-neighbour count equals `d_G − d_{G[s]}`.
Lemma 3 — `fH` (constant numbering `k`) is ≤ the rest-list size.
Main    — rest-colorable + `fH`-choosable ⇒ `Colorable k`.
Wrapper — `KCritical` supplies the rest colouring; `dG ≥ degree` is absorbed
          by antitonicity of `FChoosableZ`; contradiction with `¬ Colorable (D−1)`.
-/
import Konigsberg.Areas.Coloring.Basic
import Konigsberg.Areas.Coloring.Irreducible
import Mathlib.Combinatorics.SimpleGraph.Finite

namespace Konigsberg.Literature.Coloring.BK_ReducibleOfFChoosable

open Finset SimpleGraph
open Konigsberg.Areas.Coloring

variable {V : Type*} (G : SimpleGraph V)
variable [Fintype V] [DecidableEq V] [DecidableRel G.Adj]

set_option linter.unusedSectionVars false

/-- **Lemma 1.** The induced degree of `w` counts exactly the `G`-neighbours of `↑w`
that lie in `s`. -/
lemma degree_induce_eq_filter (s : Set V) [DecidablePred (· ∈ s)] (w : s) :
    (G.induce s).degree w
      = ((G.neighborFinset (w : V)).filter (· ∈ s)).card := by
  classical
  rw [degree]
  refine Finset.card_bij'
    (fun a _ => (a : V))
    (fun b hb => ⟨b, (Finset.mem_filter.mp hb).2⟩)
    ?_ ?_ ?_ ?_
  · intro a ha
    have hadj : (G.induce s).Adj w a := by simpa [mem_neighborFinset] using ha
    have hG : G.Adj (w : V) (a : V) := by simpa [SimpleGraph.induce, comap_adj] using hadj
    exact Finset.mem_filter.mpr ⟨(mem_neighborFinset _ _ _).mpr hG, a.2⟩
  · intro b hb
    have hbs : (b ∈ s) := (Finset.mem_filter.mp hb).2
    have hG : G.Adj (w : V) b := (mem_neighborFinset _ _ _).mp (Finset.mem_filter.mp hb).1
    have : (G.induce s).Adj w ⟨b, hbs⟩ := by
      simpa [SimpleGraph.induce, comap_adj] using hG
    simpa [mem_neighborFinset] using this
  · intro a ha; rfl
  · intro b hb; rfl

/-- **Lemma 2.** External-neighbour count `= d_G(↑w) − d_{G[s]}(w)`. -/
lemma card_external_eq (s : Set V) [DecidablePred (· ∈ s)] (w : s) :
    ((G.neighborFinset (w : V)).filter (fun u => u ∉ s)).card
      = G.degree (w : V) - (G.induce s).degree w := by
  classical
  have hsplit :=
    Finset.card_filter_add_card_filter_not (s := G.neighborFinset (w : V)) (fun u => u ∈ s)
  rw [degree_induce_eq_filter G s w, ← card_neighborFinset_eq_degree]
  rw [add_comm] at hsplit
  exact eq_tsub_of_add_eq hsplit

/-- The palette-minus-forbidden list for a core vertex, given a colouring `c₀` of
the rest. `k` is the palette size (colours `0 … k-1`). -/
noncomputable def restList (s : Set V) [DecidablePred (· ∈ s)]
    (k : ℕ) (c₀ : V → ℕ) (w : s) : Finset ℕ :=
  (Finset.range k) \ ((G.neighborFinset (w : V)).filter (fun u => u ∉ s)).image c₀

/-- **Lemma 3 (crux).** `fH` for the constant numbering `f ≡ k` is ≤ the list size. -/
lemma fH_le_card_restList (s : Set V) [DecidablePred (· ∈ s)]
    (k : ℕ) (c₀ : V → ℕ) (w : s) :
    fH G s (fun _ => (k : ℤ)) w ≤ ((restList G s k c₀ w).card : ℤ) := by
  classical
  set extN := (G.neighborFinset (w : V)).filter (fun u => u ∉ s)
  set forbidden := extN.image c₀
  have hinter_le : (forbidden ∩ Finset.range k).card ≤ forbidden.card :=
    card_le_card inter_subset_left
  have hforb_le : forbidden.card ≤ extN.card := card_image_le
  have hinter_le_k : (forbidden ∩ Finset.range k).card ≤ k := by
    simpa [card_range] using
      card_le_card (inter_subset_right : forbidden ∩ Finset.range k ⊆ Finset.range k)
  have hrest_card :
      ((restList G s k c₀ w).card : ℤ)
        = (k : ℤ) - ((forbidden ∩ Finset.range k).card : ℤ) := by
    dsimp [restList]
    rw [card_sdiff, card_range, Nat.cast_sub hinter_le_k]
  have hdle : (G.induce s).degree w ≤ G.degree (w : V) := by
    rw [degree_induce_eq_filter]
    exact (card_filter_le _ _).trans_eq (card_neighborFinset_eq_degree G _)
  have hfH : fH G s (fun _ => (k : ℤ)) w = (k : ℤ) - (extN.card : ℤ) := by
    unfold fH
    rw [card_external_eq G s w, Nat.cast_sub hdle]
  rw [hfH, hrest_card]
  exact sub_le_sub_left (Nat.cast_le.mpr (hinter_le.trans hforb_le)) _

/-- **Main lemma.** Rest `k`-colouring + `fH`-choosability of the core ⇒ `G` is
`k`-colourable. -/
theorem colorable_of_rest_and_fChoosable (s : Set V) [DecidablePred (· ∈ s)] (k : ℕ)
    (c₀ : V → ℕ)
    (hrange : ∀ v, v ∉ s → c₀ v < k)
    (hproper : ∀ ⦃u v⦄, u ∉ s → v ∉ s → G.Adj u v → c₀ u ≠ c₀ v)
    (hf : FChoosableZ (G.induce s) (fH G s (fun _ => (k : ℤ)))) :
    G.Colorable k := by
  classical
  obtain ⟨cK, hcKmem, hcKproper⟩ :=
    hf (restList G s k c₀) (fun w => fH_le_card_restList G s k c₀ w)
  refine (colorable_iff_listColorable_const G k).mpr ?_
  refine ⟨fun v => if h : v ∈ s then cK ⟨v, h⟩ else c₀ v, ?_, ?_⟩
  · intro v
    by_cases h : v ∈ s
    · simp only [h, ↓reduceDIte]
      exact (Finset.mem_sdiff.mp (hcKmem ⟨v, h⟩)).1
    · simp only [h, ↓reduceDIte]
      exact Finset.mem_range.mpr (hrange v h)
  · intro u v huv
    by_cases hu : u ∈ s <;> by_cases hv : v ∈ s
    · simp only [hu, hv, ↓reduceDIte]
      have hadj : (G.induce s).Adj ⟨u, hu⟩ ⟨v, hv⟩ := by
        simpa [SimpleGraph.induce, comap_adj] using huv
      exact hcKproper hadj
    · simp only [hu, hv, ↓reduceDIte]
      have hnot :
          cK ⟨u, hu⟩ ∉ ((G.neighborFinset u).filter (fun x => x ∉ s)).image c₀ :=
        (Finset.mem_sdiff.mp (hcKmem ⟨u, hu⟩)).2
      intro hEq
      apply hnot
      refine Finset.mem_image.mpr ⟨v, ?_, hEq.symm⟩
      exact Finset.mem_filter.mpr ⟨(mem_neighborFinset _ _ _).mpr huv, hv⟩
    · simp only [hu, hv, ↓reduceDIte]
      have hnot :
          cK ⟨v, hv⟩ ∉ ((G.neighborFinset v).filter (fun x => x ∉ s)).image c₀ :=
        (Finset.mem_sdiff.mp (hcKmem ⟨v, hv⟩)).2
      intro hEq
      apply hnot
      refine Finset.mem_image.mpr ⟨u, ?_, hEq⟩
      exact Finset.mem_filter.mpr ⟨(mem_neighborFinset _ _ _).mpr huv.symm, hu⟩
    · simp only [hu, hv, ↓reduceDIte]
      exact hproper hu hv huv

/-- `FChoosableZ` is antitone in the numbering: a smaller demand is harder. -/
lemma fChoosableZ_mono {W : Type*} [Fintype W] [DecidableEq W]
    (H : SimpleGraph W) [DecidableRel H.Adj] {f g : W → ℤ}
    (hle : ∀ w, f w ≤ g w) (hf : FChoosableZ H f) : FChoosableZ H g :=
  fun L hL => hf L fun w => (hle w).trans (hL w)

/-- Deleting a nonempty vertex set from the top subgraph yields a proper subgraph. -/
lemma deleteVerts_ne_top (s : Set V) (hs : s.Nonempty) :
    (⊤ : G.Subgraph).deleteVerts s ≠ ⊤ := by
  intro h
  obtain ⟨v, hv⟩ := hs
  have hv' : v ∈ ((⊤ : G.Subgraph).deleteVerts s).verts := by
    rw [h, Subgraph.verts_top]
    exact Set.mem_univ v
  rw [Subgraph.deleteVerts_verts, Subgraph.verts_top] at hv'
  exact hv'.2 hv

/-- Lift a colouring of `(⊤.deleteVerts s).coe` to a rest-colouring on `V`. -/
lemma exists_rest_coloring (s : Set V) [DecidablePred (· ∈ s)] (k : ℕ)
    (hcol : ((⊤ : G.Subgraph).deleteVerts s).coe.Colorable k) :
    ∃ c₀ : V → ℕ,
      (∀ v, v ∉ s → c₀ v < k) ∧
      (∀ ⦃u v⦄, u ∉ s → v ∉ s → G.Adj u v → c₀ u ≠ c₀ v) := by
  obtain ⟨C, hC⟩ := (colorable_iff_exists_bdd_nat_coloring _).mp hcol
  refine ⟨fun v => if hv : v ∈ s then 0 else C ⟨v, ?mem⟩, ?range, ?proper⟩
  case mem =>
    rw [Subgraph.deleteVerts_verts, Subgraph.verts_top]
    exact ⟨Set.mem_univ v, hv⟩
  case range =>
    intro v hv
    simpa [hv] using hC ⟨v, by
      rw [Subgraph.deleteVerts_verts, Subgraph.verts_top]
      exact ⟨Set.mem_univ v, hv⟩⟩
  case proper =>
    intro u v hu hv hadj
    have hu' : u ∈ ((⊤ : G.Subgraph).deleteVerts s).verts := by
      rw [Subgraph.deleteVerts_verts, Subgraph.verts_top]
      exact ⟨Set.mem_univ u, hu⟩
    have hv' : v ∈ ((⊤ : G.Subgraph).deleteVerts s).verts := by
      rw [Subgraph.deleteVerts_verts, Subgraph.verts_top]
      exact ⟨Set.mem_univ v, hv⟩
    have hadj' : ((⊤ : G.Subgraph).deleteVerts s).coe.Adj ⟨u, hu'⟩ ⟨v, hv'⟩ := by
      rw [Subgraph.coe_adj, Subgraph.deleteVerts_adj]
      exact ⟨Set.mem_univ u, hu, Set.mem_univ v, hv, hadj⟩
    have hne : C ⟨u, hu'⟩ ≠ C ⟨v, hv'⟩ := C.valid hadj'
    simpa [hu, hv] using hne

/-- ℕ truncation of `D − 1` is an upper bound on the ℤ value `(D : ℤ) − 1`. -/
lemma natCast_pred_le (D : ℕ) : (D : ℤ) - 1 ≤ ((D - 1 : ℕ) : ℤ) := by
  cases D with
  | zero => simp
  | succ n => simp

/-- **reducible_of_fChoosable** (BK reduction bridge; `BK.reducible_of_fChoosable`).

If `G` is `D`-critical, `s` a nonempty core, `dG` an upper bound on the ambient
degree, and `G.induce s` is `FChoosableZ` for the inline reducibility demand
`(D − 1) − (dG w − deg_{G[s]} w)`, then `False` — no such `G` exists, so the
configuration is forbidden in any minimal BK counterexample (under H_BK).

Unfolding (bridging lemmas, not bespoke): `KCritical` is the same as hereditary
subgraph-criticality `¬ Colorable (k−1) ∧ ∀ H ≠ ⊤, H.coe.Colorable (k−1)` — not
vertex-criticality alone. `FChoosableZ (↑ ∘ g)` is the same as `FChoosable g`
(`fChoosableZ_coe`); ordinary `Colorable k` is the same as `ListColorable` of the
constant `range k` lists (`colorable_iff_listColorable_const`). Demand is ℤ so
`D − 1` is not ℕ-truncated at `D = 0`. Non-vacuity witness:
`CompleteGraphKCritical.completeGraph_kCritical` (`K_k` is `k`-critical for
`k ≥ 1`). -/
theorem reducible_of_fChoosable (D : ℕ) (hcrit : KCritical G D)
    (s : Set V) [DecidablePred (· ∈ s)] (hs : s.Nonempty)
    (dG : V → ℕ) (hdeg : ∀ v, G.degree v ≤ dG v)
    (hf : FChoosableZ (G.induce s)
      (fun w : s => ((D : ℤ) - 1) - ((dG (w : V) : ℤ) - ((G.induce s).degree w : ℤ)))) :
    False := by
  classical
  let k : ℕ := D - 1
  have hrest : ((⊤ : G.Subgraph).deleteVerts s).coe.Colorable k :=
    hcrit.2 _ (deleteVerts_ne_top G s hs)
  obtain ⟨c₀, hrange, hproper⟩ := exists_rest_coloring G s k hrest
  have hle : ∀ w : s,
      ((D : ℤ) - 1) - ((dG (w : V) : ℤ) - ((G.induce s).degree w : ℤ))
        ≤ fH G s (fun _ => (k : ℤ)) w := by
    intro w
    unfold fH
    have hd : (G.degree (w : V) : ℤ) ≤ (dG (w : V) : ℤ) := Nat.cast_le.mpr (hdeg _)
    have hpred := natCast_pred_le D
    dsimp [k]
    omega
  have hfH : FChoosableZ (G.induce s) (fH G s (fun _ => (k : ℤ))) :=
    fChoosableZ_mono (G.induce s) hle hf
  have hcol : G.Colorable k :=
    colorable_of_rest_and_fChoosable G s k c₀ hrange hproper hfH
  exact hcrit.1 hcol

end Konigsberg.Literature.Coloring.BK_ReducibleOfFChoosable
