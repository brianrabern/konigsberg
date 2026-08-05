# choosability-oracle — FixerBreaker reference engine

Landon Rabern's WebGraphs `Choosability` + `BitLevelGeneration` libraries,
retargeted to modern .NET and wrapped in a JSONL CLI. Used as the differential
oracle for the Python port in `empirical/konigsberg_empirical/coloring/`.

**Kept permanently** for FixerBreaker at scale (Python is the validated
cross-check + agent tool). See PLAN §10.1 / `docs/handoff/WP_C_ORACLE.md`.

## Build

Requires the [.NET SDK](https://dotnet.microsoft.com/) (net10.0 on this machine;
adjust `<TargetFramework>` if needed). Sources are pulled from
`../../landon-tools/WebGraphs/` via `Compile Include` — do not fork them here.

```bash
# from konigsberg repo root
dotnet build vendor/choosability-oracle/ChoosabilityOracle.sln -c Release
dotnet run --project vendor/choosability-oracle/oracle/Oracle.csproj -c Release -- --selftest
```

`--selftest` must exit 0 before generating any corpus. It exercises the same
adjacency → `SuperSlimMind.Analyze` path the corpus generator uses.

### Fingerprint note

`oracle --selftest` (and `--selftest --strict`) asserts the five `MindTests.cs`
fingerprints including the nearly column. The oracle compiles a **patched**
`SuperSlimMind` (`patches/SuperSlimMind.cs`) that requires all edge lists to be
nonempty before classifying a board as nearly-colorable — boards that are only
"near" by deleting an empty-list edge are excluded. See
`docs/handoff/NEARLY_COLORABLE_ADJUDICATION.md`.

## CLI (JSONL)

One JSON object per stdin line → one JSON object per stdout line:

```json
{"n": 4, "edges": [[0,1],[1,2],[2,3]], "sizes": [3,2,2,3], "max_pot": 4}
```
```json
{"total_boards": 28, "win": false, "nearly_win": false}
```

If `win` is true, `nearly_win` is `null`.

## Corpus

```bash
uv run python tests/differential/gen_oracle_cases.py
```

Writes `tests/differential/fixtures/fixer_breaker_corpus.jsonl` (committed;
CI needs no dotnet).
