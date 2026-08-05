# Rabern Engine Port — Cursor Hand-off Plan

*Port Landon Rabern's WebGraphs choosability engine (C#) to Python, faithfully,
with faithfulness enforced by differential testing — not asserted by inspection.*

---

## 0. How to use this document

This is an implementation spec for an agent (Cursor) working **inside the
`konigsberg` repo with the WebGraphs source available alongside it**. Do the work
packages in order (A → B → C → D). Each package has: source to read, the target
Python API, an algorithm spec, and **acceptance criteria that are exact and
checkable**. Do not mark a package done until its acceptance tests pass.

The single most important rule is in §3. Read it first.

Paths:
- WebGraphs C# source: `../landon-tools/WebGraphs/` (relative to the konigsberg
  repo root; adjust if your checkout differs).
- Sage source (reference only, not in scope here): `../landon-tools/SageGraphUI/`.
- Port destination: `empirical/konigsberg_empirical/coloring/` and
  `harness/konigsberg_harness/tools/empirical_tools.py`.

---

## 1. Context & goal

Konigsberg is an agentic graph-theory research assistant. Its empirical tier is
the **solver oracle** — the layer that does the bulk of the work cheaply, so the
Lean/LLM tiers only handle the residue. Rabern's WebGraphs engine is a decade of
specialized coloring-search code and is the centerpiece of that tier.

Two capabilities to port, in priority order:

1. **Alon–Tarsi / graph polynomial** (`Choosability/Polynomials/`) — a
   *sufficient* list-colorability test via the Combinatorial Nullstellensatz.
   Self-certifying: its output is a re-checkable orientation. **Low risk.**
2. **FixerBreaker** (`Choosability/FixerBreaker/`) — a game solver for *online*
   choosability (paintability). Deep and specialized. **Higher risk**, but the
   WebGraphs unit tests give exact behavioral fingerprints to port against.

Already built in konigsberg (use as cross-checks, do not duplicate):
- `search/sat.py` — SAT `k`-/`L`-colorability (complete decision).
- `coloring/choosability.py` — CEGAR `find_bad_list` for **offline**
  `k`-choosability, with a `verify_bad_list` re-checker.
- `coloring/list_checks.py` — backtracking `find_list_coloring`, exhaustive
  `is_k_choosable` (tiny graphs).

CEGAR decides *offline* choosability; FixerBreaker decides *online*
choosability. They are different objects — see §3 — but they cross-check where
they overlap, which is exactly how we validate the port.

---

## 2. Repo map & conventions (must follow)

- **Graph type**: `konigsberg_empirical.core.Graph` — frozen dataclass
  `Graph(n: int, edges: frozenset[tuple[int,int]])`; build via
  `Graph.of(n, edges)`. Methods: `neighbors(v)`, `degree(v)`, `max_degree`.
  All ported code takes/returns this type at the package boundary.
- **Trust ledger**: `konigsberg_harness.ledger`. Tools mint Claims via
  `mint_certificate(stmt, *, checker, tool)` (CERTIFICATE),
  `mint_solver_result(stmt, *, tool)` (SOLVER),
  `mint_enumeration(stmt, *, bound, exhaustive, tool)` (ENUMERATION). **Never**
  invent a Claim by hand; never upgrade a status. A result is `certificate-checked`
  ONLY if an independent re-checker verified a finite certificate.
- **Tool registration**: `harness/.../tools/registry.py::build_registry`. Tools
  with JSON-native args (graph6 string, ints) are agent-callable; register them.
- **Tests**: `pytest`, in `tests/`. Run with both packages importable
  (`uv run pytest`, or `PYTHONPATH=harness:empirical`). Gate SAT-dependent tests
  with `pytest.mark.skipif(not <mod>.is_available(), ...)`.
- **Lint/format**: `ruff check .` must pass. 100-col lines, py311.
- **Optional deps**: `python-sat` is the `sat` extra; import lazily. If the port
  needs new deps, add them as extras, not hard requirements.
- **Differential tests** live in `tests/differential/`.

---

## 3. Ground rules — the faithfulness discipline

**READ THIS FIRST. It is the whole point of the port.**

1. **Faithfulness is verified, not claimed.** A port is correct when it
   reproduces the reference engine's output on shared inputs — not when it "looks
   right." Every ported component must have a differential test against either
   (a) the WebGraphs unit-test fingerprints, or (b) an existing konigsberg
   oracle (SAT/CEGAR), or (c) the built .NET engine (WP C).
2. **Do not port from memory of the literature.** Port from the C# source in
   `../landon-tools/WebGraphs/`. A from-scratch reimplementation of "the
   Alon–Tarsi idea" gives you *a* solver, not *Rabern's* — and the differences
   are where bugs hide. Read the actual code.
3. **Certificate beats solver.** Prefer emitting a finite, independently
   re-checkable certificate (→ `certificate-checked`) over trusting the solver's
   assertion (→ `solver-certified`). AT gives one for free (an orientation).
   FixerBreaker *can* (proof mode — see B4); until then it is `solver-certified`.
4. **Offline ≠ online choosability.** CEGAR (`find_bad_list`) decides offline
   `k`-choosability. FixerBreaker decides the online/paintability game. Do not
   test one against the other for equality in general; they agree only in
   directions the literature guarantees (e.g. online-choosable ⇒ offline-choosable,
   so a FixerBreaker "fixer wins" is consistent with CEGAR finding no bad list;
   the converse can fail). Use the WebGraphs unit tests as FixerBreaker's ground
   truth, not CEGAR.
5. **Honesty of labels.** AT is *sufficient only*: AT-good ⇒ choosable, but
   AT-failure proves nothing. Never report an AT failure as "not choosable."
6. **Faithful ≠ fast.** Python will be far slower than Rabern's bit-level C#.
   Correctness is the bar here; performance is secondary. For FixerBreaker
   specifically, expect the Python port to be a validated cross-check and the
   agent-facing tool — the compiled engine may remain the production oracle for
   large graphs (see WP C/D). Do **not** silently narrow the algorithm to make it
   fast; match behavior first, optimize second, and only behind a differential
   test.

---

## 4. Source map (WebGraphs)

Graph type and I/O:
- `Choosability/Graph.cs` — the reference `Graph`. Built from edge weights
  (`Graph(List<int> edgeWeights, ...)`), also `Graph(bool[,] adjacent, ...)`.
  API you'll mirror/bridge: `N`, `this[x,y]`, `Degree(v)`, `Neighbors`,
  `OutDegree`, `InDegreeSequence`, `EnumerateOrientations(...)`,
  `CountSpanningEulerianSubgraphs(out even, out odd)`.
- `.graph` file format (see `UnitTests/TestGraphs/*.graph`): JSON,
  `{"Edges":[{"IndexV1","IndexV2","Multiplicity","Orientation",...}], ...}` plus
  vertex labels used to derive the pot/template.

Alon–Tarsi:
- `Choosability/Polynomials/GraphPolynomial.cs` — `GetCoefficient(int[] power)`,
  `GetSignSum(int[] power)`. Recursion over prior neighbors with exact rationals.
- `Choosability/Polynomials/{Normalizer,SignLookup,FactoredRational,PrimeNumbers}.cs`
  — exact-arithmetic helpers.
- Usage / orientation search: `Console/FindChoosables.cs` (see `CheckOrientation`,
  `EnumerateOrientations`), `Console/Extensions.cs`, `Console/MixedChoosables.cs`.

FixerBreaker (the deep one):
- Entry: `Choosability/FixerBreaker/KnowledgeEngine/Slim/Super/SuperSlimMind.cs`
  (`Analyze(Template) -> bool`, `TotalBoards`, `MaxPot`,
  `OnlyConsiderNearlyColorableBoards`, `BoardCounts`).
- Board + moves: `.../Slim/Super/SuperSlimBoard.cs`, `SuperSlimSwapAnalyzer.cs`,
  `Hashing.cs`, `GameTree.cs`; coloring test `SuperSlimColoringAnalyzer` (find in
  the same subtree).
- Template: `Choosability/FixerBreaker/KnowledgeEngine/Template.cs`
  (`Sizes: List<int>`; string forms `dK`/`pK` = degree±K).
- Proof/certificate layer (for B4): `.../Slim/Super/Proofs/*` (`ProofBuilder`,
  `PermutationAwareProofBuilder`, `MaximumDegreeThreeProofBuilder`), `GameTree.cs`,
  `SuperSlimMind` with `proofFindingMode: true`.
- Reference (unoptimized) variants for cross-checking your port internally:
  `FixerBreaker/Board.cs`, `SlowBoard.cs`, `KnowledgeEngine/Mind.cs`.

Behavioral fingerprints (ground truth): `UnitTests/MindTests.cs` +
`UnitTests/TestGraphs/*.graph`. See the exact table in §6.

---

## 5. Work Package A — Alon–Tarsi / graph polynomial

**Goal:** a faithful port of the graph-polynomial coefficient computation and the
orientation search that yields the Alon–Tarsi list-colorability certificate.

### A.1 Target module & API
`empirical/konigsberg_empirical/coloring/alon_tarsi.py` (the current stub —
replace it). Suggested API:

```python
def graph_polynomial_coefficient(graph: Graph, power: list[int]) -> int: ...
def sign_sum(graph: Graph, power: list[int]) -> int: ...
def count_eulerian_subgraphs(orientation) -> tuple[int, int]:  # (even, odd)
    ...
def alon_tarsi_number(graph: Graph) -> int: ...            # min k s.t. AT-good orientation with maxoutdeg = k-1
def certificate(graph: Graph, f: list[int] | None = None): ...   # an AT-good orientation (out-degrees < f), or None
def verify_certificate(graph: Graph, cert) -> bool: ...          # independent re-check
```

The existing harness tool `empirical_tools.alon_tarsi(graph)` already expects
`certificate()` + `verify_certificate()`; keep those names/signatures so it wires
up unchanged.

### A.2 Algorithm spec (from the source)
- Graph polynomial `P_G = ∏_{uv∈E, u<v} (x_u − x_v)`. Port `GraphPolynomial`'s
  `SumTerms`/`GetCoefficient` exactly (recursion over `_priorNeighbors`, exact
  `FactoredRational` arithmetic). The coefficient of `∏ x_v^{power[v]}` being
  nonzero ⇒ `G` is `L`-colorable for any lists with `|L(v)| = power[v] + 1`.
- An orientation `D` is **AT-good** iff `#even ≠ #odd` spanning Eulerian
  subgraphs, equivalently the coefficient at the out-degree monomial is nonzero.
  Port **both** checks (`CountSpanningEulerianSubgraphs` and the coefficient
  route in `CheckOrientation`) — they cross-check each other internally.
- Orientation search: mirror `FindChoosables.CheckOrientation` +
  `Graph.EnumerateOrientations(v => degree(v) + 1 - f(v))`, deduping by
  in-degree sequence.
- **Certificate** = the AT-good orientation (its out-degree sequence + the
  witnessing nonzero coefficient). `verify_certificate` recomputes the
  coefficient / Eulerian counts from scratch — no trust in the search.

### A.3 Tests & acceptance
`tests/test_alon_tarsi.py`:
1. **Coefficient values**: pick ~5 small graphs; assert
   `graph_polynomial_coefficient` matches a from-definition brute-force expansion
   of `P_G` (write the brute-force in the test as the oracle).
2. **Two-route agreement**: coefficient-nonzero ⇔ Eulerian even≠odd, over all
   graphs up to n=6 (use `enumerate.all_graphs`).
3. **AT number sanity**: even cycle → 2, odd cycle → 3, `K_n` → n, trees → 2.
4. **Certificate**: `verify_certificate(g, certificate(g))` is `True` whenever a
   certificate is returned; and AT-good ⇒ CEGAR finds no bad list at
   `k = alon_tarsi_number` (one-directional cross-check with
   `choosability.find_bad_list`).
5. **Honesty**: assert the tool never claims "not choosable" from an AT failure.

**Done when:** all of the above pass, `ruff` clean, and
`empirical_tools.alon_tarsi` mints `certificate-checked` on a hit.

---

## 6. Work Package B — FixerBreaker / SuperSlimMind

**Goal:** a faithful port of `SuperSlimMind.Analyze`, validated against exact
`TotalBoards` + win fingerprints from `MindTests.cs`.

### B.0 Ground-truth fingerprints (non-negotiable acceptance)
From `UnitTests/MindTests.cs` + `UnitTests/TestGraphs/`. `TestGraph(name,
totalPositions, shouldWin, shouldWinNearlyColorable)`:

| graph file | TotalBoards | fixer wins | wins (nearly-colorable mode) |
|---|---|---|---|
| `P_4_good.graph` | 28 | false | true |
| `P_4_bad.graph` | 40 | false | false |
| `long_3_claw_very_good.graph` | 2336 | true | (n/a — already won) |
| `long_3_claw_good.graph` | 3488 | false | true |
| `long_3_claw_bad.graph` | 5216 | false | false |

Template derivation used by the tests: `potSize = max vertex label`; per-vertex
size = `potSize + degree(v) − label(v)`; `mind.MaxPot = potSize`. The
nearly-colorable runs set `OnlyConsiderNearlyColorableBoards = true`.

`TotalBoards` is an algorithmic fingerprint: reproducing it exactly means you
enumerate the identical position space. **This is the port's pass/fail gate.**

### B.1 Target API
`empirical/konigsberg_empirical/coloring/fixer_breaker.py` (replace stub). Mirror
the reference:

```python
@dataclass
class Template:
    sizes: list[int]

class SuperSlimMind:
    def __init__(self, graph: Graph, *, proof_finding=False, swap_mode=..., reduction_mode=...): ...
    max_pot: int
    only_consider_nearly_colorable_boards: bool
    total_boards: int          # set by analyze()
    board_counts: list[int]
    def analyze(self, template: Template) -> bool:  # True == fixer wins
        ...
```

Plus a `.graph` loader + template helper so the fingerprint tests can run:
```python
def load_dotgraph(path) -> tuple[Graph, list[int]]:   # (graph, vertex labels)
def template_from_labels(graph, labels) -> tuple[Template, int]:  # (template, pot_size)
```

### B.2 Algorithm spec (from `SuperSlimMind.Analyze`)
1. For `colorCount` in `[max(MinPot, max size), min(MaxPot, sum sizes)]`,
   `EnumerateAllBoards(template, colorCount)`. `TotalBoards = len(all boards)`.
2. Classify: `FindColorableBoards` (fixer already won — colorable position),
   `FindNearlyColorableBoards` (only in the restricted mode),
   `FindSuperabundantBoards`, `FindReducibleBoards`.
3. Game fixpoint (`Analyze(progress)` private): propagate fixer/breaker-won
   status through swap moves (`SuperSlimSwapAnalyzer`), using canonical board
   hashing (`Hashing`) for dedup.
4. Return `BreakerWonBoards.Count <= 0` (fixer wins iff no breaker-won board
   survives), after intersecting with nearly-colorable/superabundant sets per the
   flags.

Port the board representation (`SuperSlimBoard`), the swap analyzer, the coloring
analyzer, and the hashing **faithfully** — these determine both `TotalBoards` and
the verdict.

### B.3 Suggested porting phases (decompose the risk)
- **B3a — Graph bridge + `.graph` loader + `Template`.** Confirm the loader
  reproduces the test graphs' degree sequences and derived template sizes.
- **B3b — Board enumeration + coloring analyzer only.** Get `TotalBoards` and
  `BoardCounts[0]` (colorable count) to match the fingerprints **before** writing
  any game logic. This isolates enumeration faithfulness from game faithfulness —
  if `TotalBoards` is wrong, the game verdict is meaningless. Match 28 / 40 /
  2336 / 3488 / 5216 here.
- **B3c — Swap analyzer + game fixpoint.** Now match `shouldWin` and the
  nearly-colorable verdicts.
- **B3d — Optional internal cross-check.** Port the unoptimized
  `SlowBoard`/`Mind` path and assert it agrees with `SuperSlimMind` on the test
  graphs (a second, independent faithfulness signal).

### B.4 Certificate path (stretch → `certificate-checked`)
Investigate `proofFindingMode` + `Proofs/*` + `GameTree.cs`. If FixerBreaker can
emit a winning-strategy object, port a `verify_strategy(graph, template, proof)`
independent re-checker and upgrade the tool from `solver-certified` to
`certificate-checked`. Until then, `empirical_tools.fixer_breaker` mints
`solver-certified` (as it does now).

### B.5 Tests & acceptance
`tests/test_fixer_breaker.py`:
1. **Fingerprint tests** (the §6.0 table) — exact `total_boards`, `analyze()`
   verdict, and nearly-colorable verdict for all 5 graphs. **Non-negotiable.**
2. B3d cross-check (if implemented): slow vs super agree on all 5.
3. Consistency with CEGAR **only in the guaranteed direction** (online fixer-win
   ⇒ offline no-bad-list): where `analyze()` says fixer wins at pot k, assert
   `choosability.find_bad_list(graph, k)` is `None`. Do **not** assert the
   converse.

**Done when:** the fingerprint table passes exactly, `ruff` clean, and the tool
is registered (JSON-native args → agent-callable) minting the right trust root.

---

## 7. Work Package C — .NET oracle (for differential scale)

The five unit-test fingerprints are a strong start but small. To widen the net
toward the plan's retirement bar (agreement up to n=10 + sampled larger), build
the reference engine and generate `(graph → verdict, TotalBoards)` at volume.

- **Note:** the konigsberg sandbox has no `dotnet`/`mono`. This package is done on
  a dev machine (macOS) with the .NET SDK or Mono. It is a prerequisite for
  *broad* differential coverage, not for the fingerprint tests (those run without
  it).
- Tasks: build the `Choosability` class library and `Console` project (WebGraphs
  is .NET-Framework-era; the class lib likely builds under modern .NET/Mono with
  minor csproj tweaks; the Silverlight UI projects are out of scope). Add a small
  headless entry that reads a graph (graph6 or `.graph`) and prints
  `TotalBoards`, the win verdict, and (for AT) the certificate. Run `MindTests`
  to confirm the build reproduces the fingerprints.
- Deliverable: a script `tests/differential/gen_oracle_cases.py` (or a shell
  wrapper) that drives the built engine over `enumerate.all_graphs`/geng output
  and writes `(graph6, k/template, verdict, total_boards)` records for the
  differential suite.

---

## 8. Work Package D — differential harness, vendor, retirement

- Place the built reference engine (or its recorded outputs) under
  `vendor/choosability-oracle/` (subprocess-callable), per the plan.
- `tests/differential/`: for each ported capability, feed shared inputs to the
  Python port and the oracle (or recorded oracle outputs) and assert identical
  results. AT: coefficient + certificate agreement. FixerBreaker: verdict +
  `TotalBoards` agreement.
- **Retirement bar** (from PLAN §7): agreement across all graphs up to n=10 plus
  a sampled set of larger ones. Only then delete the live `.NET` build and pin
  tests against recorded oracle outputs. **Exception:** for FixerBreaker,
  consider keeping the compiled engine as the production oracle for large graphs
  (Python is a validated cross-check + agent tool). Decide per §10.

---

## 9. Sequencing & acceptance gates

1. **WP A (Alon–Tarsi)** — self-contained, self-certifying, cross-checks against
   CEGAR. Ship first. Gate: §5.3.
2. **WP B (FixerBreaker)** — the crux. Gate: §6.0 fingerprint table passes
   exactly (do B3b's `TotalBoards` match before B3c's verdicts).
3. **WP C (.NET oracle)** — Brian/dev-machine; unblocks broad differential
   coverage.
4. **WP D (differential + retirement)** — continuous; gates `vendor/` deletion.

Every package: `ruff check .` clean, `uv run pytest` green, new tools registered
in `build_registry`, Claims minted with the correct trust root, and a
differential test present.

---

## 10. Open decisions for Brian

1. **FixerBreaker retirement.** Delete `vendor/` after n≤10 agreement (per plan),
   or keep the compiled engine as the production oracle for large graphs with the
   Python port as validated cross-check? (Recommendation: keep it — Python will
   be too slow at scale.)
2. **AT scope.** Port only the coefficient + orientation search now, or also the
   downstream AT utilities in `Console/` (mixed choosability, derivative method)?
3. **.NET build target.** Modern .NET SDK vs Mono for the oracle build — whichever
   you can get building the `Choosability` lib fastest on your machine.
4. **Certificate for FixerBreaker (B4).** Is a re-checkable winning-strategy
   worth the extra work to reach `certificate-checked`, or is `solver-certified`
   (port validated against the oracle) sufficient for now?
