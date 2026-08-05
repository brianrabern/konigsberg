# Adjudicating the nearly-colorable discrepancy (Cursor spec)

*Two artifacts by the same (now deceased) author disagree, so there is no
authority to appeal to. We settle it from the definition, the published data, and
an independent clean-room computation — then lock the answer with a test.*

## Verdict (resolved)

**Probe 1:** Stable across 20 fresh processes — not an RNG/order bug.

**Probe 2:** Six leftover ∩ nearly survivors on `P_4_good`; all have an **empty
middle-edge list**. Independent classifier agreed with the engine that they are
"colorable without that edge" — but that is a vacuous nearness (delete the edge
that has no colors).

**Probe 3:** Clean-room `(L,P)`-fixability (Cranston–Rabern Def., not vertex
paintability — SuperSlimMind is edge-coloring fixability) agrees:
- non-strict nearly → `nearly_win = false` (matches unpatched engine);
- **strict nearly** (all edge lists nonempty + colorable after deleting one edge)
  → `nearly_win = true` for `*_good`, `false` for `*_bad` — matches MindTests.

**Fix:** require all edge lists nonempty before classifying a board as
nearly-colorable (Python `_nearly_colorable`; C# oracle patch
`vendor/choosability-oracle/patches/SuperSlimMind.cs`). MindTests fingerprints
restored; corpus regenerated; `--selftest --strict` encodes the intended column.

---

## The dispute

For the "good" fixtures (`P_4_good`, `long_3_claw_good`):
- **`MindTests.cs` asserts** `nearly_win = true`.
- **The current engine (and the faithful Python port) return** `false`.

`TotalBoards` and outright-`win` match `MindTests` exactly on all five fixtures.

## What is already established (do not re-litigate)

1. **The game is f-paintability with f(v) = d(v) − 1** (Rabern's published BK
   "online" data: <https://landon.github.io/graphdata/borodinkostochka/online/>).
   The fixer-breaker game = the Lister/Painter online list-coloring game.
2. **Naming encodes intent:** "very good" = outright fixer win; **"good" = fixer
   wins restricted to nearly-colorable boards**; "bad" = neither. So "good" is
   *defined* to have `nearly_win = true`.
3. **It is not a template bug.** `TotalBoards` is a function of (template,
   max_pot, enumeration); it matches `MindTests` exactly, so the template
   derivation is provably identical. The divergence is isolated to the
   nearly-colorable classification or the restricted-game fixpoint.
4. **Equality is content-based**, so the millisecond-seeded `Hashing` RNG affects
   only bucket/enumeration order, not counts — unless a code path is
   order-dependent (Probe 1 checks this).
5. **Definitional reference:** "Edge-coloring via fixable subgraphs"
   (Cranston–Rabern, arXiv 1507.05600) defines "fixable" and the nearly-colorable
   refinement. Also his dissertation *Coloring graphs from almost maximum degree
   sized palettes*.

**Prior (state it honestly):** published data + names + his own tests all say the
"good" graphs are nearly-colorable-fixable (`true`); the current engine says
`false`. The most likely conclusion is a **regression in the engine's nearly
path that the port faithfully copied**, with `MindTests` reflecting the intended
mathematics. The probes below confirm this rather than assume it.

## Probe 1 — determinism (rule out the RNG hash)

Run the oracle on `P_4_good` in nearly mode ~20 times (fresh process each).
- **Flips** across runs → nearly path is order-dependent; the RNG hash makes it
  ill-defined. Fix: seed `Hashing`'s RNG with a constant, rebuild, re-derive.
  Then the value is well-defined; continue.
- **Stable** → not nondeterminism; go to Probe 2.

## Probe 2 — dissect `P_4_good` (28 boards, hand-checkable)

Instrument the nearly run to dump, for `P_4_good`:
- `|NearlyColorableBoards|`, `|BreakerWonBoards|`, `|remaining|`;
- the exact board(s) in `(BreakerWonBoards ∪ remaining) ∩ NearlyColorableBoards`
  (these are why it returns `false`).

For each such survivor board B, check independently:
- **(a) Is B really nearly-colorable?** Re-run `ColorableWithoutEdge(B, e)` from a
  standalone re-implementation for each edge e; confirm it matches the engine's
  classification. If the engine marks B nearly-colorable but it isn't → the
  classifier is the bug.
- **(b) Should the fixpoint have marked B fixer-won?** Solve the game from B with
  the independent solver (Probe 3). If Painter wins from B but the engine left it
  as breaker-won/remaining → the fixpoint/ordering is the bug.

This localizes the regression to classifier vs. fixpoint (or shows the survivor
is legitimate → the "good" label was aspirational, which would contradict the
published data and should itself be double-checked).

## Probe 3 — clean-room solver (the tie-breaker)

Write an **independent** f-paintability solver that owes nothing to Rabern's
board encoding — a plain recursive Lister/Painter game — and confirm it against
the outright values first, then use it for the nearly question.

**Game (f-paintability, f(v) = d(v) − 1 here):**
- State: for each vertex, remaining token count `tok[v]` (init `f(v)`), and a
  `colored` flag.
- A round: **Lister** picks a nonempty set `M` of uncolored vertices. **Painter**
  picks an independent (in G) subset `I ⊆ M`; vertices in `I` become colored;
  each vertex in `M∖I` loses one token (`tok -= 1`).
- **Painter loses** if some uncolored vertex hits `tok < 0` (marked with no tokens
  left and not colored). **Painter wins** when all vertices are colored.
- G is **f-paintable** iff Painter has a winning strategy (Painter wins under
  optimal Lister play). Solve by minimax with memoization on the state.

**Validation of the clean-room engine:** it must reproduce the *outright* results
independently — Painter loses (not f-paintable) for `P_4_good`/`P_4_bad`
(outright `win = false`), Painter wins for `long_3_claw_very_good`. If it does,
the clean-room engine is trustworthy.

**The nearly question, independently:** the "nearly-colorable restricted" win is:
Painter is only required to win from game positions ("boards") that are
nearly-colorable (colorable after deleting one edge). Compute it as: enumerate the
reachable boards; Painter wins-nearly iff every board from which Painter has *no*
winning continuation is **not** nearly-colorable (i.e. all unavoidable losing
positions are excluded by the nearly restriction). Implement this over the
clean-room game + an independent nearly-colorable predicate. Compare to the
engine.

`P_4` is tiny (n=4, f = degree−1), so full minimax is instant.

## Decision rule

- Clean-room `nearly_win(P_4_good) = true` (matching published data / names /
  MindTests) and engine returns `false` → **confirmed engine regression**. Fix
  the nearly path (Probe 2 localized it) so the port reproduces `MindTests`;
  restore the strict fingerprints (including the nearly column); remove the
  `xfail`. Re-generate the differential corpus.
- Clean-room `= false` → the published/naming intuition is wrong for this exact
  template, which would be surprising; re-examine the nearly-colorable *definition*
  used (Probe 2a) before trusting it. Do not "fix" toward either value until the
  clean-room and the definition agree.

## Lock it down

- Re-instate a `--selftest --strict` in the oracle asserting the `MindTests`
  nearly column, so the intended values are encoded, not just documented.
- Keep the ledger label for nearly-colorable **provisional** until Probe 3
  confirms; then promote to solver-certified (validated against the clean-room
  solver + corpus).
- Outright-win / `TotalBoards` and the offline CEGAR BK tooling are unaffected
  throughout — only the nearly-colorable verdict is in question.

## Sources
- BK online data (f = d−1 paintability): <https://landon.github.io/graphdata/borodinkostochka/online/>
- Edge-coloring via fixable subgraphs (definition of fixable / nearly): arXiv 1507.05600
- Dissertation: *Coloring graphs from almost maximum degree sized palettes*
  (landon.github.io)
