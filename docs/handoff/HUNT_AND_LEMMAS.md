# Hunt mode + working lemma notebook

Two related gaps: proofs died with the Lean process, and the agent stopped
whenever the model emitted a chat final — even with nothing proved.

## Working notebook (lock + read back)

Every successful `lean_prove` locks `(lean_name, snippet)` on the session
JSONL. That is **not** Literature and does **not** mint extra trust: the
ledger Claim is still the only proved record. The notebook is source
retention so the investigation can reuse its own lemmas.

| Surface | What it does |
|---|---|
| `lemma_list` | names + durable/session tags |
| `lemma_read name` | full locked snippet |
| `/lemmas` | same catalog in the REPL |
| `--resume` / `--continue` | replay snippets into a fresh Lean env |
| `/reset` | drop ephemeral decls, **then replay locks** |

`durable=True` still means “self-contained against the corpus” and is still
required for `/promote`. After a durable prove the snippet is also installed
in the session env so later lemmas can depend on it.

## Hunt — go until proved

Not chat. The loop ignores prose finals and injects a continue until
`lean_prove` mints a kernel proof (or Ctrl-C / round cap).

```bash
uv run konig --until-proved --task "Prove Nat.add_comm for 0"
uv run konig --until-proved --require-durable --task "…"
uv run konig --until-proved --max-rounds 400 --task "…"
uv run konig --continue --until-proved   # resume the last investigation
```

In the REPL: `/hunt <goal>`.

Stop condition is **`lean_prove` only** (not `verify_coloring`, not solver
claims). `--require-durable` waits for a promotable snippet.

## Forever — Borodin–Kostochka campaign

Open-ended on ordinary lemmas. Uses the full instrument (literature,
reducible configurations, empirical BK tools, Lean, locked lemmas) and
**builds on Rabern's results** already in the corpus (list bounds,
list-critical edge bounds, BasicIrreducible, Ore-Vizing, hitting cliques,
Cranston–Rabern reducible configurations) until the **conjecture itself**
is settled, or Ctrl-C. Session + notebook persist;
`--continue --forever` resumes.

Stop conditions (ledger only — model prose never counts):

| Outcome | What has to be on the ledger |
|---|---|
| Proved | durable `lean_prove` of `BorodinKostochka` whose snippet looks like χ ≤ max{Δ−1, ω} for Δ ≥ 9 |
| Disproved | `bk_predicate` certificate that a graph **VIOLATES BK** (Δ ≥ 9) |

A lemma, a `satisfies BK` check, a `bk_search` hit in the deg-{3,4} family,
or a finite sweep does **not** halt the campaign. A durable kernel proof of
`borodinKostochka` does — that Claim is a proof of the conjecture.

```bash
uv run konig --forever
make campaign
uv run konig --continue --forever
```

Needs a live model (`KONIGSBERG_PROVIDER=local` + llama.cpp, or an Anthropic
key). In the REPL: `/forever`. Clone-to-campaign (local LLM):
[`docs/LOCAL_BK_HUNT.md`](../LOCAL_BK_HUNT.md).

A finite sweep still never proves BK. Progress is locked lemmas, **new**
forbidden cores, and kernel subproofs — the ledger stays honest.

The continue prompt is not a generic “Continue.” It injects a **staircase**
from the ledger: locked lemma names, distinct `core=` graph6 strings already
forbidden, and the first incomplete increment (bridge proof → new core →
lemmas used by `borodinKostochka`). `campaign_status` is the same snapshot
as a tool. Retesting a listed core comes back as **REDISCOVERY** and is not
progress. If the stair fingerprint freezes (same cores, same durable lemmas,
same discharging miss) across injections, the continue prompt surfaces
**REFORMULATE**: trade BK for an a-priori-weaker equivalent
(`CranstonRabern_BKEquivalentConjectures`) where choosability bites — do not
drop the stair. After compaction the snapshot is re-injected so the stair survives
chat rewrite.

Chat mode is unchanged: one user message → ≤40 steps → prose final still
stops, and a lying “I proved it” still mints nothing.
