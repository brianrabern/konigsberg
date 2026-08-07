# Statements-first ingestion of the coloring book (Cursor spec)

*Make the whole Rabern book a visible, queryable corpus of open targets — not a
plan in a doc. Right now `literature_search` surfaces only the two proven list
bounds and three stated papers; the bulk of the book (kernel magic, Nullstellensatz,
Brooks-list, the BK-endgame clique structure) is invisible to the agent. Add the
remaining book theorems as `stated` Literature entries — Statements.lean typechecks,
Proofs.lean is `sorry`, status.toml `stated` — in dependency order. This turns the
roadmap into concrete proof targets the agent can find and aim at.*

Source spine: `basic graph coloring.tex` (primary — definitions, list-coloring,
irreducibility, kernel magic, Nullstellensatz) and `gct.tex` (BK-endgame clique
structure, Menger). Key every entry to the book's exact label/section.

## The discipline (this is the whole point)

- **A statement-first entry's deliverable is the *statement*.** Faithfulness is
  everything: `Statements.lean` must state the book's actual theorem — right
  quantifiers, right hypotheses, no weakening, no trivialization. **A wrong
  statement is worse than no entry**, because `literature_search` will surface it
  and a future proof will aim at the wrong target. This is the definitional-fidelity
  ceiling we already hit with the K₄ misindexing — take it seriously here.
- Each entry mirrors the existing template
  (`RabernBook_FirstListBound/`): `Statements.lean` (typechecks, `sorry`-free
  *statement*, theorem body `:= sorry` or `by sorry`), `Proofs.lean` (imports
  Statements; proof `sorry`), `status.toml` (`status = "stated"`, `lean_name`,
  citation = book §, `verified_at` = HEAD), `Notes.md` (the book's proof sketch +
  what machinery a real proof needs).
- **Fidelity review per entry:** after it typechecks, re-read the statement against
  the `.tex` and confirm it says the theorem and nothing weaker. Record the check
  in `Notes.md`. Use `lean_typecheck_statement` to confirm it elaborates as a Prop.
- `check_status`/`check_no_sorry`/`check_axioms` already tolerate `stated` entries
  (the three existing ones pass CI) — no gate changes needed. Do **not** mark any of
  these `formalized`.

## WP0 — Minimal definitions to *state* each group (Areas/Coloring)

Only what's needed to write the statements — not to prove them. Build per group,
just ahead of the entries that need it:

- **Kernel machinery:** `kernel` (independent + dominating in an orientation) and
  `kernelPerfect` on the existing `Orientation` (`Orientation.lean`).
- **Graph polynomial:** `graphPolynomial` `p_G ∈ MvPolynomial V ℤ` = `∏_{uv∈E}(x_u−x_v)`;
  the coefficient / `p_k(G)`, and even/odd Eulerian subdigraph counts `EE`, `EO`
  (mathlib `MvPolynomial`). Enough to *state* the Nullstellensatz group.
- **Clique collection machinery:** clique number `ω` (reuse mathlib `cliqueNum`/
  `IsNClique` if available, else define), max-degree `Δ` (mathlib `maxDegree`),
  the max-clique collection `𝒬`, and the clique-intersection graph `X_𝒬`. Needed
  for the entire BK-endgame tier.
- **Gallai tree** + degree-choosability are already in `Basic.lean`
  (`DegreeChoosable`) — extend only if the Brooks-list statement needs `GallaiTree`.

## Tier A — book core (`basic graph coloring.tex`), dependency order

Create `Literature/Coloring/<Label>/` for each:

1. **`BasicIrreducible`** — f-irreducible ⇒ `f(v) ≤ d(v)`, hence `2|E| ≥ f(V)`.
   The seed of every edge bound. Machinery exists (`Irreducible.lean`); if it's
   already a green Areas lemma, add the Literature entry that *cites* it as
   `formalized` (not `stated`) — otherwise state it. (Check which.)
2. **`KernelPerfectListBound`** and **`KernelPerfectSuperListBound`** — the
   kernel-perfect generalization of the list bound (needs WP0 kernel defs).
3. **`KostochkaYanceyKernelLemma`** — the kernel lemma underneath (4)–(5).
4. **Nullstellensatz group** — `CombinatorialNullstellensatz` (the coefficient
   criterion), `EulerianOrientationsLemma` (`p_k(G) = |EE| − |EO|`), and the
   `SchauzCoefficient` formula. **These are the formal statements the empirical
   `alon_tarsi`/`polynomials.py` certificates correspond to** — state them so that
   proving them later turns an AT certificate into a witness of a formalized
   theorem. Make the `lean_name`s the exact propositions the empirical tier targets.
5. **`BrooksListForm`** — the list-coloring form of Brooks (Gallai-tree
   characterization of degree-choosability). Cross-reference the external
   `BrooksLean` entry in `Notes.md` (ordinary Brooks, external-verified) — this is
   the in-tree list version, distinct.
6. **`DeltaEdgeColoring`** — edge coloring toward BK-for-line-graphs.

## Tier B — BK-endgame clique structure (`gct.tex`), dependency order

Closest to the north star; all need WP0 clique machinery. State early even though
proofs stay `sorry` — they give the agent the real targets.

1. **`HajnalLemma`** — for max cliques `𝒬`: `|⋃𝒬| + |⋂𝒬| ≥ 2ω(G)`. Base counting
   lemma; needs only cliques + `ω`.
2. **`KostochkaCliqueGraph`** — `ω(G) > ⅔(Δ+1)` ∧ `X_𝒬` connected ⇒ `⋂𝒬 ≠ ∅`.
3. **`TwoThirdsEqualityStructure`** — the `ω ≥ ⅔(Δ+1)` boundary case dichotomy.
4. **`TransitiveClusteringBigCliques`** — connected vertex-transitive `G` with
   `ω ≥ ⅔(Δ+1)`: `X_𝒬` edgeless, or a cycle of blown-up `K_{ω/2}`.

## Empirical tie (do the Nullstellensatz names deliberately)

The Nullstellensatz statements (A4) are the spec for `alon_tarsi.py` /
`polynomials.py`. Name and shape them so that a future proof of
`EulerianOrientationsLemma` lets an Alon–Tarsi certificate be checked against a
*formalized* statement — a genuine empirical→formal bridge instance, like
`verify_coloring` but for AT. Note this correspondence in each Notes.md.

## Verification

- Every `Statements.lean` typechecks in-tree (`lean_check` / CI lean job).
- `check_status` sees each new entry as `stated`; CI stays green.
- Per-entry fidelity review recorded in `Notes.md` (statement vs `.tex`).
- `literature_search("kernel")`, `("Nullstellensatz")`, `("Hajnal")`,
  `("Brooks")` each return the new stated entries at status `stated only`.

## Acceptance

- All Tier A + Tier B theorems exist as `stated` Literature entries, statements
  typechecking, keyed to the book's labels/sections, faithful (reviewed).
- The book is now discoverable end-to-end via `literature_search` — the agent can
  see the whole open-target corpus, not just the 2 proven + 3 stated papers.
- WP0 definitions are in `Areas/Coloring` (enough to state; proofs deferred).
- No entry marked `formalized`; CI green; `ruff`/tests unaffected.

## Scope discipline

- **State, don't prove.** Proofs stay `sorry`. Resist proving the easy-looking ones
  in the same pass — that's a separate, later effort, and mixing them risks half-done
  entries. (Exception: `BasicIrreducible` if it's already a green Areas lemma — then
  cite it as `formalized`.)
- **Faithfulness over coverage.** Better five correct statements than ten sloppy
  ones. A weakened or mis-quantified statement is a latent trap.
- Define only enough machinery to state each theorem; don't build proof
  infrastructure speculatively.
- Order matters: WP0 machinery just ahead of the entries that need it; Tier A
  before Tier B (endgame depends on clique machinery).
