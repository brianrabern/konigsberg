# External formalizations (not in-tree)

Artifacts verified under a **different pinned toolchain** than Konigsberg's
`formal/` lake pin. They are **not** the same trust root as an in-tree
`status = "formalized"` / ledger `proved` Claim: Konigsberg's gates
(`check_no_sorry`, `check_axioms --run-lean`, `check_status`) were not run on
these declarations inside this repo.

Status label used here:

| Status | Meaning |
|---|---|
| **external-verified** | Verified no-`sorry` / clean axioms under a different pinned toolchain we did not run through our own gates; explicitly **not** the same trust root as an in-tree `proved`; pending in-tree re-verification at Konigsberg's next mathlib bump. |

---

## BrooksLean — Brooks' theorem (Rabern form)

| Field | Value |
|---|---|
| Repo | <https://github.com/brianrabern/BrooksLean> |
| Commit | `1d990050d881327fc79dd51e82ba4449b4e2467d` |
| Lean | `v4.33.0-rc1` (`leanprover/lean4:v4.33.0-rc1`) |
| mathlib pin | `cb48454af87fbe318fc368e6eb02c9156e1936c1` |
| Konigsberg pin (for contrast) | Lean `v4.31.0` — **do not** treat this entry as in-tree |
| Status | **external-verified** |
| Stage-0 date | 2026-08-07 |
| Vetting env | BrooksLean's own `lake` / toolchain (not Konigsberg's) |

### Statement (`SimpleGraph.brooks`)

As elaborated in BrooksLean (faithful Rabern form: not-Δ-colorable ⇒ contains
`K_{Δ+1}`, or Δ = 2 and an odd cycle):

```lean
theorem brooks (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj]
    (h : ¬ G.Colorable G.maxDegree) :
    ¬ G.CliqueFree (G.maxDegree + 1) ∨ (G.maxDegree = 2 ∧ G.HasOddCycle)
```

`#check` output (verbatim):

```
SimpleGraph.brooks.{u} {V : Type u} (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj]
  (h : ¬G.Colorable G.maxDegree) : ¬G.CliqueFree (G.maxDegree + 1) ∨ G.maxDegree = 2 ∧ G.HasOddCycle
```

### Statement faithfulness (Stage 0)

- **Hypothesis** is `¬ G.Colorable G.maxDegree`, i.e. χ(G) = Δ(G)+1 (using χ ≤ Δ+1).
- **Conclusion** is exactly `¬ CliqueFree (Δ+1)` (contains a clique of size Δ+1) **or**
  `(Δ = 2 ∧ HasOddCycle)` — nothing weaker, no extra hypotheses that trivialize
  the claim (only `[Fintype V]` / `[DecidableRel G.Adj]` for finite decidable graphs).
- **`HasOddCycle`** is the honest odd-cycle predicate:
  `∃ v c, c.IsCycle ∧ Odd c.length`, backed by
  `colorable_two_iff_not_hasOddCycle : G.Colorable 2 ↔ ¬ G.HasOddCycle`.

### No-`sorry` check (Stage 0)

- `lake build` in BrooksLean: **Build completed successfully** (warnings only;
  no errors).
- Grep of `*.lean`: the only occurrence of the word `sorry` is a **doc-comment**
  in `Brooks.lean` stating the proof has no `sorry`. No `sorry` / `sorryAx` /
  `native_decide` in proof terms.

### Axiom audit (Stage 0) — verbatim

```
'SimpleGraph.brooks' depends on axioms: [propext, Classical.choice, Quot.sound]
```

Within Konigsberg's whitelist (`propext`, `Classical.choice`, `Quot.sound`).
**No** `sorryAx`. **No** `Lean.ofReduceBool`.

Supporting intermediate also clean:

```
'SimpleGraph.colorable_two_iff_not_hasOddCycle' depends on axioms: [propext, Classical.choice, Quot.sound]
```

### Verdict

**external-verified.** BrooksLean’s `SimpleGraph.brooks` is a faithful, no-`sorry`,
whitelist-axiom formalization of Brooks’ theorem under mathlib
`cb48454af87fbe318fc368e6eb02c9156e1936c1` / Lean `v4.33.0-rc1`. It is **not**
an in-tree Konigsberg `formalized` entry; Stage 2 (copy into
`Literature/Coloring/RabernBrooks/`, re-verify under Konigsberg’s pin) waits on a
deliberate mathlib bump (≥ v4.33), not a casual drop-in.
