# Ingesting BrooksLean into Konigsberg (Cursor spec)

*`github.com/brianrabern/BrooksLean` is a no-`sorry` Lean formalization of Brooks'
theorem (Rabern's proof). Bring its content into Konigsberg's `Literature` tier —
but only through the trust gates, never trusted-by-import. The artifact was
produced by an agentic loop, so vetting it IS the point: it tests whether the loop's
output survives Konigsberg's discipline.*

## What's there (already checked)

- **Statement (faithful).** `SimpleGraph.brooks (G) [Fintype][DecidableRel]
  (h : ¬ G.Colorable G.maxDegree) : ¬ G.CliqueFree (G.maxDegree + 1) ∨
  (G.maxDegree = 2 ∧ G.HasOddCycle)`. This is Rabern's form: not-Δ-colorable ⇒
  contains `K_{Δ+1}` or (Δ=2 and an odd cycle). `¬ Colorable maxDegree` = χ = Δ+1
  (χ ≤ Δ+1 always). `HasOddCycle` is defined honestly (`∃ closed walk, IsCycle ∧
  Odd length`, with `colorable_two_iff_not_hasOddCycle` backing it). Built on
  mathlib's `Colorable`/`maxDegree`/`CliqueFree` — aligns with Konigsberg's
  `KCritical`/`Colorable` bridge.
- **No `sorry`** anywhere (only a doc-comment mentions the word). 2270 LOC over
  `OddCycle.lean`, `VertexLemmas.lean`, `Brooks.lean`.
- **Version:** Lean `v4.33.0-rc1`, mathlib pinned to commit
  `cb48454af87fbe318fc368e6eb02c9156e1936c1` (needs `neighborFinset_sup`).
  **Konigsberg is on `v4.31.0`.** This gap is the only real obstacle.

## The gate that blocks a naive drop-in

Konigsberg's `formalized` status means: builds **in-tree, under Konigsberg's
pinned mathlib**, passing `check_no_sorry` / `check_axioms --run-lean` /
`check_status`. BrooksLean builds under a *different, newer* mathlib. So it cannot
be marked `formalized` in-tree today without either (a) bumping Konigsberg to
≥v4.33 — a deliberate whole-project move that also drags the `repl` pin and the
freshly-verified `Basic.lean` — or (b) back-porting Brooks to v4.31 (unknown API
churn; the `neighborFinset_sup` note suggests real drift). Neither is worth doing
casually, and **neither is on the BK critical path.** So stage it.

## Stage 0 — version-independent vetting (do now, in BrooksLean's own env)

These establish the artifact's mathematical trust regardless of version:

1. **Axiom audit.** In BrooksLean, `#print axioms SimpleGraph.brooks`. Confirm the
   list is within Konigsberg's whitelist — `propext`, `Classical.choice`,
   `Quot.sound` — with **no `sorryAx`** and **no `Lean.ofReduceBool`**
   (native_decide). Record the exact output.
2. **Statement faithfulness (human/agent read).** Confirm `brooks` says Brooks and
   nothing weaker: the hypothesis is genuinely χ=Δ+1, `HasOddCycle` is the honest
   odd-cycle predicate (it is — verified), and there are no extra hypotheses that
   trivialize it. Do the same for any intermediate theorem you plan to cite.

If Stage 0 passes, the artifact is mathematically trustworthy on its own terms —
that's the "did the loop produce something real?" verdict.

## Stage 1 — link as external-verified (do now)

Do **not** fake an in-tree `formalized` entry. Instead:

- Add `docs/handoff/` or a new `Literature/EXTERNAL.md` registry entry recording:
  BrooksLean repo URL + commit, mathlib pin, the `brooks` statement, the Stage-0
  axiom output, and the status **`external-verified`** (verified no-`sorry` /
  clean-axioms under mathlib `cb48454…`, pending in-tree re-verification at the
  next Konigsberg mathlib bump).
- Cross-link: PLAN §6 (Literature) and README note BrooksLean as an external,
  independently-built formalization — the origin being the Opus-5 loop — that will
  be pulled in-tree when versions align.
- Keep the ledger honest: `external-verified` is explicitly **not** the same trust
  root as an in-tree `proved`. It means "verified under a different pinned
  toolchain we did not run in our gates." Add this as a documented provenance
  category so the distinction is visible, not blurred.

## Stage 2 — real in-tree integration (later, gated on a mathlib bump)

When Konigsberg makes its next **deliberate** mathlib bump to ≥ v4.33 (a separate
decision — it moves the `repl` pin and requires re-verifying `Basic.lean`):

1. Copy `OddCycle.lean`, `VertexLemmas.lean`, `Brooks.lean` into
   `formal/Konigsberg/Literature/Coloring/RabernBrooks/` (namespace under
   `Konigsberg.Literature.Coloring.RabernBrooks`, or keep `SimpleGraph`-namespaced
   lemmas in a clearly-scoped file). Reconcile any names that shifted between
   `cb48454…` and Konigsberg's pinned commit.
2. `lake build`; then `check_no_sorry`, `check_status`, `check_axioms --run-lean`
   on the entry. `status.toml`: `status = "formalized"`, `axioms = [...]` from the
   live `#print axioms`, `citation` = Rabern, *Yet another proof of Brooks'
   theorem*, Discrete Math. 346 (2023) 113261.
3. Promote from `external-verified` → `formalized`. Now it's a first-class corpus
   theorem, and a public demonstration that the trust spine can adjudicate
   agentic output.

## Keep the repo separate

BrooksLean stays its own public repo (the experiment/demo — clean standalone
story). Konigsberg *cites and re-verifies* it; it does not vendor it as a
submodule that bypasses the gates.

## Priority

After `M2_FIRREDUCIBLE.md` (f-irreducibility is the BK critical path). Stage 0 is
cheap and can be done anytime. Stage 2 rides the next mathlib bump — don't trigger
that bump just for Brooks; let it happen when the formal tier needs ≥v4.33 for
other reasons, then absorb Brooks in the same pass.
