/-
Areas/Coloring — the exemplar vertical. Definitional layer (M2).

HUMAN-OWNED, REVIEWED. Definitions translated from the Cranston–Rabern /
Kierstead–Rabern list-coloring literature (see PLAN §6 and docs/handoff). A wrong
definition here makes true theorems unprovable or trivially false, so they are
written to be *checked*, not guessed. Modeling decisions, stated explicitly:

  * COLORS ARE ℕ. Choosability quantifies over all list assignments; letting the
    color type vary would force universe quantification inside a `Prop`. Fixing
    colors to ℕ is WLOG — any finite palette injects into ℕ and L-colorability is
    preserved under injective recoloring. (That equivalence is left as a future
    lemma; the ℕ form is the working definition.)
  * f-CHOOSABILITY is the general notion (a list-size requirement per vertex);
    k-choosability is its constant instance. Literature often states this for
    exact-size `f`-assignments (`|L v| = f v`); the ≥ form here is equivalent
    (trim each list to size `f v`).
  * k-LIST-CRITICAL follows Cranston–Rabern: not `(k-1)`-choosable, but every
    proper subgraph is `(k-1)`-choosable. Formalized via `SimpleGraph.Subgraph`
    (vertex deletion changes the vertex type to a subtype — `H.coe`).
  * EDGE-f-CRITICAL is the edge-minimal weakening (delete any one edge →
    `f`-choosable). Edge lower bounds only need this; it is implied by full
    list-criticality, and for `k ≥ 2` coincides with it under subgraph
    monotonicity of choosability.

Typechecked against mathlib v4.31 (`lake build Konigsberg.Areas.Coloring.Basic`).
-/
import Mathlib.Combinatorics.SimpleGraph.Coloring.Vertex
import Mathlib.Combinatorics.SimpleGraph.Finite
import Mathlib.Combinatorics.SimpleGraph.Subgraph
import Konigsberg.Foundations.Basic

namespace Konigsberg.Areas.Coloring

open Finset Function

variable {V : Type*} (G : SimpleGraph V)

/-- A list assignment gives each vertex a finite set of permitted colors (in ℕ). -/
abbrev ListAssignment (V : Type*) := V → Finset ℕ

/-- `c` is a proper coloring of `G`: adjacent vertices receive distinct colors. -/
def IsProperColoring (c : V → ℕ) : Prop :=
  ∀ ⦃u v⦄, G.Adj u v → c u ≠ c v

/-- `G` is `L`-colorable: some proper coloring draws each vertex's color from its
own list. (Erdős–Rubin–Taylor / Vizing; the load-bearing definition.) -/
def ListColorable (L : ListAssignment V) : Prop :=
  ∃ c : V → ℕ, (∀ v, c v ∈ L v) ∧ IsProperColoring G c

/-- `G` is `f`-choosable: every list assignment with `f v ≤ |L v|` at each vertex
admits a proper `L`-coloring. Equivalent to the literature's formulation over
exact-size `f`-assignments. -/
def FChoosable (f : V → ℕ) : Prop :=
  ∀ L : ListAssignment V, (∀ v, f v ≤ (L v).card) → ListColorable G L

/-- `G` is `k`-choosable: `f`-choosable for the constant function `k`. -/
def Choosable (k : ℕ) : Prop := FChoosable G (fun _ => k)

/-- The choice number / list-chromatic number chₗ(G) = χₗ(G): the least `k` for
which `G` is `k`-choosable. `noncomputable`; well-defined for finite `G`
(`choosable_card` witnesses the defining set is nonempty). -/
noncomputable def choiceNumber : ℕ := sInf {k | Choosable G k}

section Finite
variable [Fintype V] [DecidableRel G.Adj]

/-- `G` is degree-choosable (`d₀`-choosable): `f`-choosable for `f v = deg(v)`.
Subject of the Borodin / Erdős–Rubin–Taylor characterization (Gallai trees). -/
def DegreeChoosable : Prop := FChoosable G (fun v => G.degree v)

end Finite

/-- Edge-`f`-critical: `G` is not `f`-choosable, but deleting any single edge makes
it `f`-choosable. The edge-minimal form used by Cranston–Rabern edge lower
bounds; weaker than full subgraph-criticality only in degenerate `k = 1` cases. -/
def EdgeFCritical (f : V → ℕ) : Prop :=
  ¬ FChoosable G f ∧ ∀ ⦃e⦄, e ∈ G.edgeSet → FChoosable (G.deleteEdges {e}) f

/-- `G` is `k`-list-critical (Cranston–Rabern): not `(k-1)`-choosable, yet every
proper subgraph is `(k-1)`-choosable. -/
def KListCritical (k : ℕ) : Prop :=
  ¬ Choosable G (k - 1) ∧
    ∀ (H : G.Subgraph), H ≠ ⊤ → Choosable H.coe (k - 1)

/-- Alias matching PLAN / handoff naming. -/
abbrev ListCritical (k : ℕ) : Prop := KListCritical G k

/-- Edge-`k`-list-critical: not `(k-1)`-choosable, yet every single-edge deletion
is `(k-1)`-choosable. -/
def EdgeKListCritical (k : ℕ) : Prop := EdgeFCritical G (fun _ => k - 1)

/-- `G` is `k`-critical (chromatic, Gallai): not `(k-1)`-colorable, but every
proper subgraph is `(k-1)`-colorable. -/
def KCritical (k : ℕ) : Prop :=
  ¬ G.Colorable (k - 1) ∧
    ∀ (H : G.Subgraph), H ≠ ⊤ → H.coe.Colorable (k - 1)

/-- Edge-`k`-critical: not `(k-1)`-colorable, but every single-edge deletion is. -/
def EdgeKCritical (k : ℕ) : Prop :=
  ¬ G.Colorable (k - 1) ∧ ∀ ⦃e⦄, e ∈ G.edgeSet → (G.deleteEdges {e}).Colorable (k - 1)

/- ── Connecting lemmas ─────────────────────────────────────────────────────
These confirm the definitions compose with mathlib and with each other. -/

/-- Ordinary `k`-colorability is `L`-colorability for the constant list `range k`.
The bridge between mathlib's `Colorable` and `ListColorable`. -/
theorem colorable_iff_listColorable_const (k : ℕ) :
    G.Colorable k ↔ ListColorable G (fun _ => Finset.range k) := by
  constructor
  · rintro ⟨C⟩
    refine ⟨fun v => (C v : ℕ), fun v => ?_, ?_⟩
    · exact Finset.mem_range.mpr (C v).isLt
    · intro u v h hc
      exact (C.valid h) (Fin.val_injective hc)
  · rintro ⟨c, hmem, hproper⟩
    refine ⟨SimpleGraph.Coloring.mk
      (fun v => (⟨c v, Finset.mem_range.mp (hmem v)⟩ : Fin k)) ?_⟩
    intro u v h hc
    exact hproper h (congrArg Fin.val hc)

/-- Choosability dominates colorability: a `k`-choosable graph is `k`-colorable
(instantiate choosability at the constant list `range k`). -/
theorem Choosable.colorable {k : ℕ} (h : Choosable G k) : G.Colorable k := by
  apply (colorable_iff_listColorable_const G k).mpr
  exact h (fun _ => Finset.range k) (fun v => by simp [Finset.card_range])

/-- Every graph on `n` vertices is `n`-choosable (colour greedily). Hence the set
defining `choiceNumber` is nonempty for finite graphs, so `choiceNumber` is a
genuine minimum.

Proof: induct over a finset `s` of coloured vertices; when adding `a`, its already
-coloured neighbours use `< |s| < n ≤ |L a|` colours, so `L a` has a free one. -/
theorem choosable_card [Fintype V] : Choosable G (Fintype.card V) := by
  classical
  intro L hL
  suffices h : ∀ s : Finset V, ∃ c : V → ℕ,
      (∀ v ∈ s, c v ∈ L v) ∧ (∀ u ∈ s, ∀ v ∈ s, G.Adj u v → c u ≠ c v) by
    obtain ⟨c, hmem, hproper⟩ := h Finset.univ
    exact ⟨c, fun v => hmem v (Finset.mem_univ v),
      fun u v huv => hproper u (Finset.mem_univ u) v (Finset.mem_univ v) huv⟩
  intro s
  induction s using Finset.induction with
  | empty => exact ⟨fun _ => 0, by simp, by simp⟩
  | @insert a s ha ih =>
    obtain ⟨c, hmem, hproper⟩ := ih
    -- colours already used by neighbours of `a`
    set bad : Finset ℕ := (s.filter (fun b => G.Adj a b)).image c with hbad
    have hbad_card : bad.card < (L a).card := by
      have hle : bad.card ≤ s.card :=
        (Finset.card_image_le).trans (Finset.card_filter_le _ _)
      have hins : s.card < Fintype.card V := by
        have hcard : (insert a s).card ≤ Fintype.card V := Finset.card_le_univ _
        rw [Finset.card_insert_of_notMem ha] at hcard
        omega
      have hLa : Fintype.card V ≤ (L a).card := hL a
      omega
    have hne : (L a \ bad).Nonempty := by
      rw [← Finset.card_pos]
      have := Finset.le_card_sdiff bad (L a)
      omega
    obtain ⟨x, hx⟩ := hne
    rw [Finset.mem_sdiff] at hx
    obtain ⟨hxL, hxbad⟩ := hx
    refine ⟨update c a x, ?_, ?_⟩
    · intro v hv
      rcases Finset.mem_insert.mp hv with rfl | hvs
      · rwa [update_self]
      · rw [update_of_ne (by rintro rfl; exact ha hvs)]; exact hmem v hvs
    · intro u hu v hv huv
      rcases Finset.mem_insert.mp hu with (rfl | hus)
      · -- u = a
        rcases Finset.mem_insert.mp hv with (rfl | hvs)
        · exact absurd huv (G.loopless.irrefl _)
        · rw [update_self, update_of_ne (by rintro rfl; exact ha hvs)]
          intro hc
          exact hxbad (hbad ▸ Finset.mem_image.mpr
            ⟨v, Finset.mem_filter.mpr ⟨hvs, huv⟩, hc.symm⟩)
      · -- u ∈ s
        rcases Finset.mem_insert.mp hv with (rfl | hvs)
        · rw [update_of_ne (by rintro rfl; exact ha hus), update_self]
          intro hc
          exact hxbad (hbad ▸ Finset.mem_image.mpr
            ⟨u, Finset.mem_filter.mpr ⟨hus, huv.symm⟩, hc⟩)
        · rw [update_of_ne (by rintro rfl; exact ha hus),
              update_of_ne (by rintro rfl; exact ha hvs)]
          exact hproper u hus v hvs huv

end Konigsberg.Areas.Coloring
