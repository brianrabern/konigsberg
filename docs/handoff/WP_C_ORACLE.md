# WP C — .NET Oracle & Differential Harness (Cursor spec)

*Stand up Rabern's compiled engine as ground truth, self-validate it against the
five fingerprints, then generate a broad differential corpus that both validates
the already-faithful outright-win port AND becomes the substrate for fixing
nearly-colorable mode without overfitting.*

Prereq: `dotnet` is available on the build machine. This spec assumes the
konigsberg repo + `../landon-tools/WebGraphs/` source.

---

## 0. Why this before finishing nearly-colorable

The nearly-colorable divergence currently has **four** ground-truth data points
(the nearly columns of the five fixtures). Fixing a subtle solver bug against four
answers produces an *overfit* fix that passes those four and stays wrong in
general — exactly the silent-porting-bug failure the differential architecture
exists to prevent. The oracle turns the fix into a broad check. Build it first;
fix nearly-colorable against its corpus second.

**Hard gate:** the oracle must reproduce the five `MindTests` fingerprints
(28 / 40 / 2336 / 3488 / 5216 + win + nearly) *through the exact code path the
corpus generator uses* before it is trusted for anything. A corpus from an
unvalidated oracle is worse than no corpus.

---

## 1. Build the oracle (minimal surface)

Good news from the source: `Choosability/Choosability.csproj` is a Portable Class
Library (Profile24) depending only on `System`, `System.Core`, and
`BitLevelGeneration` — **no System.Drawing / Windows / Silverlight**. So it is
pure computational code and retargets cleanly.

Steps:
1. Create a modern solution referencing **only** two existing projects,
   retargeted to `net8.0`: `Choosability` and `BitLevelGeneration`. Do **not**
   pull in `GraphicsLayer`, `SLPropertyGrid`, `WebGraphs.Web`, `PictureMaker`,
   `Console` (net45, UI-ish), or `UnitTests` (MSTest/net45).
   - Simplest path: add new SDK-style `.csproj` files (`<TargetFramework>net8.0`,
     `<LangVersion>latest`) that `Compile Include` the existing `.cs` files, or
     do an in-place SDK-style migration of those two projects. Fix any net40-ism
     that trips net8 (rare in pure compute code).
2. Add a new console project `oracle/` (net8.0, `OutputType=Exe`) referencing
   `Choosability`. This is the only new C# code. Keep it tiny — it is glue.
3. Confirm `dotnet build` is clean.

Place the built exe (or the whole `oracle/` project) under
`konigsberg/vendor/choosability-oracle/` per PLAN §4, subprocess-callable.

---

## 2. Oracle CLI contract (JSONL, stream-friendly)

The oracle reads **one JSON object per line** on stdin and writes **one JSON
object per line** on stdout, in order. This mirrors the LeanREPL framing and lets
the Python driver stream a whole corpus through one process.

**Input line:**
```json
{"n": 4, "edges": [[0,1],[1,2],[2,3]], "sizes": [2,3,3,2], "max_pot": 3}
```
- `edges`: undirected, 0-indexed, each pair once.
- `sizes`: per-vertex template list sizes, length `n` (the `Template.Sizes`).
- `max_pot`: sets `mind.MaxPot`.

**Output line:**
```json
{"total_boards": 28, "win": false, "nearly_win": true}
```
- `total_boards` = `mind.TotalBoards` after `Analyze`.
- `win` = outright fixer win = `mind.Analyze(template)`.
- `nearly_win` = re-run on a fresh mind with
  `OnlyConsiderNearlyColorableBoards = true`, `Analyze` again. (If `win` is true,
  emit `nearly_win = null` — nearly mode is moot; mirrors the unit tests.)

**Graph construction (do exactly this):** build a `bool[,] adjacent` from `edges`
and call `new Choosability.Graph(adjacent)`. Then, mirroring `MindTests.TestGraph`:
```csharp
var mind = new SuperSlimMind(G) { MaxPot = maxPot };
var template = new Template(sizes);            // Choosability.FixerBreaker.KnowledgeEngine.Template
var win = mind.Analyze(template, null);
int total = mind.TotalBoards;
bool? nearly = null;
if (!win) {
    var m2 = new SuperSlimMind(G) { MaxPot = maxPot, OnlyConsiderNearlyColorableBoards = true };
    nearly = m2.Analyze(template, null);
}
```

Also implement `--selftest` (see §3). Everything else (multiple color counts,
etc.) is already inside `Analyze`; do not reimplement it in the CLI.

---

## 3. Self-validation gate (`oracle --selftest`)

Before the oracle may generate any corpus, `--selftest` must pass. It exercises
the oracle's **own** input→output path (not MSTest) so the corpus generator's
exact code path is what gets validated:

For each of `tests/fixtures/rabern_graphs/{P_4_good,P_4_bad,long_3_claw_very_good,
long_3_claw_good,long_3_claw_bad}.graph`:
- parse the `.graph` JSON (keys: `Vertices` with `Label`, `Edges` with
  `IndexV1`/`IndexV2`);
- `potSize = max(int(Label))`; `sizes[v] = potSize + degree(v) - int(Label[v])`;
  `max_pot = potSize`;
- run the §2 path and assert against:

| graph | total_boards | win | nearly_win |
|---|---|---|---|
| P_4_good | 28 | false | true |
| P_4_bad | 40 | false | false |
| long_3_claw_very_good | 2336 | true | (null) |
| long_3_claw_good | 3488 | false | true |
| long_3_claw_bad | 5216 | false | false |

Exit non-zero on any mismatch. (Optionally also run the C# `MindTests` as a
second signal, but `--selftest` is the authoritative gate because it validates the
adjacency-construction path the corpus uses, which `MindTests`' `.graph` path does
not.)

---

## 4. Python side — corpus generation + differential test

Two files under `tests/differential/` (Cursor owns this dir):

### 4a. `gen_oracle_cases.py` (run manually, needs the oracle)
- Enumerate graphs via `konigsberg_empirical.search.enumerate.all_graphs`
  (geng when present). **Cap size** for the committed corpus — start `n ≤ 7`,
  a modest sweep (Python `fixer_breaker` and even the oracle blow up with big
  templates; `TotalBoards` grows fast).
- **Template rule** (document it; the point is agreement, not a specific coloring
  question): for each graph emit two cases — `sizes[v] = degree(v)` with
  `max_pot = max(sizes)`, and the same with `max_pot = max(sizes) + 1` — to
  exercise multiple color counts. Skip graphs where `max(sizes) == 0`.
- Stream all cases through the oracle (one subprocess, JSONL). Write records to
  `tests/differential/fixtures/fixer_breaker_corpus.jsonl`:
  `{"graph6": ..., "n": ..., "edges": ..., "sizes": ..., "max_pot": ...,
    "total_boards": ..., "win": ..., "nearly_win": ...}`.
- **Commit the corpus.** This is what lets the differential test run in CI with
  no dotnet (per PLAN §8 "pin recorded oracle outputs").

### 4b. `test_fixer_breaker_differential.py` (runs in CI, no dotnet)
- Load the committed corpus. `skipif` the file is absent.
- For each record, run the Python `fixer_breaker` engine on the same
  `edges/sizes/max_pot` and assert `total_boards`, `win`, and `nearly_win` all
  match the recorded oracle values.
- Mark the heavier cases `@pytest.mark.slow` so the default suite stays fast (see
  §6).

This is the broad faithfulness check: exact `TotalBoards` + verdict agreement
across the whole corpus, not five graphs.

---

## 5. Then: fix nearly-colorable against the corpus

Only after §4 exists: fix `OnlyConsiderNearlyColorableBoards` mode (Cursor's own
hypothesis: leftover `∩ nearly` classification) and require the **corpus**
`nearly_win` column to match — not just the four fixtures. Remove the `xfail` in
`test_fixer_breaker.py` when the corpus agrees. If the corpus reveals the bug is
broader than the fixtures suggested, that is the oracle doing its job.

---

## 6. Test-suite hygiene (do alongside)

- Add a `slow` marker (`pyproject.toml [tool.pytest.ini_options] markers`) and tag
  the `long_3_claw` fingerprint tests and the heavy differential cases `@slow`.
- Default `pytest` deselects `slow` (e.g. `addopts = "-m 'not slow'"`); a
  dedicated CI job runs `-m slow`. Keeps the everyday suite < ~30s given the
  ~43s `long_3_claw` cost.

---

## 7. Retirement bar & vendor

- Widen the corpus toward the PLAN §7 bar: agreement across all graphs up to a
  chosen `n` (target n≤10 as compute allows) plus a sampled larger set.
- **Decision already taken (PLAN §10.1 / earlier):** do **not** delete the .NET
  engine for FixerBreaker. Python is the validated cross-check and agent tool; the
  compiled oracle stays as the production engine for large graphs. Keep
  `vendor/choosability-oracle/` and the committed corpus.

---

## 8. Acceptance criteria

- `oracle --selftest` reproduces the five fingerprints via the CLI path; exits 0.
- `gen_oracle_cases.py` produces a committed `fixer_breaker_corpus.jsonl`.
- `test_fixer_breaker_differential.py` passes (Python == oracle on the whole
  corpus for `total_boards` + `win`; `nearly_win` after §5).
- `xfail` removed from the nearly-colorable tests; §6 `slow` split in place.
- `ruff` clean; oracle build reproducible from a documented `dotnet build`.

---

## Open decisions for Brian (resolved / noted during WP C)

1. **Corpus size cap.** Started at `n ≤ 5` (94 records) for a CI-friendly committed
   corpus. Widen with `gen_oracle_cases.py --max-n 6|7` as compute allows.
2. **Template rule.** `sizes = degree(v)` at `max_pot ∈ {Δ, Δ+1}` as proposed.
3. **Retarget.** New SDK-style csprojs under `vendor/choosability-oracle/` that
   `Compile Include` landon-tools sources (no fork). Target framework: `net10.0`
   (machine SDK); adjust if needed.
4. **MindTests nearly column.** Resolved by strict nearly-colorable (all edge
   lists nonempty). See `docs/handoff/NEARLY_COLORABLE_ADJUDICATION.md`.