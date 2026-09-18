# Clone the repo and run the Borodin–Kostochka hunt on a local LLM

This is the clone-to-campaign walkthrough. It assumes you want **no cloud
API key**: Lean, the empirical solvers, the agent loop, and the model all
run on your machine. The target is the Borodin–Kostochka (BK) conjecture:

> every graph with maximum degree Δ ≥ 9 satisfies χ ≤ max{Δ−1, ω}.

That is a theorem you can prove. The Lean statement is
`Konigsberg.Literature.Coloring.BorodinKostochka.borodinKostochka` (status
`stated`, proof `sorry`). `--forever` runs until a **durable kernel
`lean_prove`** of that statement lands on the ledger — or a certified
Δ ≥ 9 counterexample, or you stop it. Model prose never counts. A long
run with only empirical Claims is unfinished work, not a failed design:
the same loop is how a proof gets in.

`--forever` does not retract the project non-goal of “autonomous proof of
open conjectures” (`PLAN.md`). It is an instrumented search. Settlement is
still a kernel proof (or a certified Δ ≥ 9 counterexample), not a pile of
empirical Claims.

**What to read:** this file, then [`TRUST.md`](TRUST.md) and
[`../README.md`](../README.md). `docs/handoff/` is a lab notebook — ignore
it unless you are debugging a specific ingest. `vendor/` is a **test
oracle** for differential tests; do not build it to run the hunt (those
tests skip if it is missing).

Shorter notes this document supersedes for operators: [`handoff/LOCAL_LLM.md`](handoff/LOCAL_LLM.md)
(llama.cpp wiring) and [`handoff/HUNT_AND_LEMMAS.md`](handoff/HUNT_AND_LEMMAS.md)
(hunt vs forever). Project overview and trust model: [`../README.md`](../README.md)
and [`TRUST.md`](TRUST.md).

---

## What you are turning on

Three tiers, none of which import each other:

| Tier | Where | Role in the hunt |
|---|---|---|
| Formal | `formal/` | Lean 4.31 + mathlib + Konigsberg library + Literature corpus. `lean_prove` is kernel-checked. |
| Empirical | `empirical/` | Graph construction, choosability, `reducible_configuration`, `bk_predicate`. |
| Harness | `harness/` | Agent loop, tools, ledger, sessions. Talks to both tiers via subprocess. |

The LLM only **proposes** tool calls. Claims are minted by tools (`lean_prove`,
`bk_predicate`, `reducible_configuration`, …), never by the model. That is
true of Opus and of a local 32B coder. A local model that drives `lean_prove`
to a closed proof of `borodinKostochka` has proved BK; a fluent model that
only talks has not.

`--forever` is the BK campaign. It ignores ordinary lemmas and chat finals.
It stops only on:

| Outcome | Ledger condition |
|---|---|
| **Proved** | durable `lean_prove` whose `lean_name` contains `BorodinKostochka` and whose snippet is χ ≤ max{Δ−1, ω} for Δ ≥ 9, kernel-checked, no `sorry` |
| **Disproved** | `bk_predicate` certificate that a graph **VIOLATES BK** (Δ ≥ 9) |
| Operator | Ctrl-C, or `--max-rounds N` if you set a cap |

The imported corpus decl still has `sorry`; the scratch env cannot overwrite
it. Settlement is a **complete theorem** in the `lean_prove` snippet (same
statement, `lean_name` containing `BorodinKostochka`). That Claim is the
proof.

A `satisfies BK` check, a forbidden configuration, a locked lemma, or a
finite sweep does **not** halt the campaign — those are increments toward
the kernel proof, not substitutes for it.

`--until-proved` is a different mode: it stops on the **first** successful
`lean_prove`. Do not use that for the BK campaign.

---

## Hardware and software you need

### Machine

- **GPU VRAM** for a 27B/32B Qwen coder GGUF at Q4_K_M or Q5_K_M. 24 GB is
  a realistic floor for 32B Q4; 48 GB+ is comfortable. 8B-class models will
  demo the CLI and miss tools often — they are not a hunt engine.
- **System RAM** on top of VRAM if you partially offload.
- **Disk**: several GB for mathlib oleans (`lake exe cache get`) plus the
  GGUF (roughly 16–20 GB for 32B Q4_K_M).
- **CPU** is fine for Lean and the Python solvers; the bottleneck is the
  local LLM and occasional SAT/enumeration.

This guide is written around **llama.cpp `llama-server`** (ROCm, CUDA, or
Metal). vLLM, Ollama, and LM Studio work if they speak OpenAI
`/v1/chat/completions` with **native tool calls**. The harness is stdlib
HTTP — no `anthropic` extra is required on this path.

### Software

| Tool | Why |
|---|---|
| Git | clone |
| Python ≥ 3.11 | harness + empirical |
| [`uv`](https://docs.astral.sh/uv/) | workspace install (`uv sync`, `uv run konig`) |
| [`elan`](https://lean-lang.org/lean4/doc/setup.html) | Lean toolchain manager; pin is `leanprover/lean4:v4.31.0` in `formal/lean-toolchain` |
| `lake` | comes with the Lean toolchain; builds `formal/` |
| nauty (`geng` or `nauty-geng`) | graph enumeration; `make deps` installs via brew/apt when missing |
| `llama-server` | OpenAI-compatible local model |
| `curl`, `tmux` (or equivalent) | health check; long soaks |

Optional: Homebrew on macOS (nauty). You do **not** need an Anthropic key.

---

## 1. Clone and enter the repo

```bash
git clone <this-repo-url> konigsberg
cd konigsberg
```

Work from the **repository root** for `uv run konig`, `make deps`, and
`.env`. Lean commands run inside `formal/`.

---

## 2. Python workspace and nauty

```bash
# uv: https://docs.astral.sh/uv/
uv sync
make deps          # uv sync + nauty/geng (brew/apt/dnf/pacman when missing)
```

`make deps` is `uv run python scripts/ensure_deps.py --yes`. Confirm:

```bash
uv run konig --help
which geng || which nauty-geng
```

Without `geng`, empirical enumeration tools degrade; the hunt can still
build named graphs (`make_graph`) and run Lean.

---

## 3. Lean + mathlib (do this once; it is the slow step)

Do **not** compile mathlib from source. Use the official cache.

```bash
cd formal
lake update                 # writes lake-manifest.json (already committed; leave it)
lake exe cache get          # prebuilt mathlib oleans
lake build                  # Konigsberg + REPL exe
cd ..
```

Or: `make lean-setup` from the repo root (same three lake commands).

Sanity:

```bash
make lean-smoke             # LeanREPL round-trip
```

The interactive agent starts `lake exe repl` in `formal/` and, on first
`lean_check` / `lean_prove`, loads:

```lean
import Konigsberg
import Mathlib.Tactic
open SimpleGraph Finset Function
open Konigsberg.Areas.Coloring
```

`import Konigsberg` only sees **compiled oleans**. If you pull new
Literature sources and skip `lake build`, `#check` of corpus lemmas is
`Unknown identifier`. The harness rebuilds `Konigsberg` automatically when
any `formal/Konigsberg/**/*.lean` is newer than `Konigsberg.olean`. A full
`lake build` after clone still avoids a surprise pause on the first Lean
tool call.

Lean 4.31 imports are **not** a substitute for a current barrel olean.
Building a single Literature module is not enough; the root `Konigsberg`
target must be current.

---

## 4. Start llama-server

Use an **Instruct / Coder / tool-use** GGUF, not a base checkpoint.

Good fits:

- Qwen2.5-Coder-32B-Instruct
- Qwen3-Coder (32B or 30B-A3B MoE)
- Qwen2.5-32B-Instruct (weaker at tools than the coder variants)

Quantization: Q4_K_M or Q5_K_M is the usual 27/32B sweet spot; Q8 if VRAM
allows.

**Required server flags**

| Flag | Why |
|---|---|
| `--jinja` | native tool-calling template; without it Qwen dumps XML into prose |
| `--ctx-size 32768` (or more) | tool schemas + Lean snippets are large |
| `--chat-template-kwargs '{"enable_thinking": false}'` | Qwen3 “thinking” fights tool use |

Example (adjust the GGUF path and GPU backend):

```bash
llama-server \
  -m /path/to/Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf \
  --host 127.0.0.1 \
  --port 8080 \
  --ctx-size 32768 \
  --jinja \
  --chat-template-kwargs '{"enable_thinking": false}' \
  -ngl 99
```

`-ngl 99` offloads every layer to GPU (ROCm/CUDA/Metal as your llama.cpp
was built). Leave this process running in its own terminal or tmux pane.

Health check:

```bash
curl -s http://127.0.0.1:8080/v1/models
```

You want a JSON model list, not a connection error.

### Other OpenAI-compatible servers

Point `OPENAI_BASE_URL` at any `/v1` that implements `chat/completions`
with `tools`. llama.cpp often **ignores** the `model` field when a single
GGUF is loaded; `KONIGSBERG_MODEL` is still what the Konigsberg banner
shows. If the server was started with `--api-key`, set `OPENAI_API_KEY` to
the same value (the harness defaults the header to `local` otherwise).

Aliases the harness accepts for the base URL: `OPENAI_BASE_URL`,
`KONIGSBERG_LLM_BASE_URL`, `LLAMA_CPP_BASE_URL`. A URL without `/v1` gets
`/v1` appended.

---

## 5. Point Konigsberg at the server (`.env`)

Repo-root `.env` is **gitignored**. Copy the committed template:

```bash
cp .env.example .env
# then edit KONIGSBERG_MODEL / OPENAI_BASE_URL if needed
```

The CLI loads `.env` at startup (`harness/konigsberg_harness/envfile.py`).
Shell exports win; `.env` does not override variables already in the
environment.

Minimum contents (already in `.env.example`):

```
KONIGSBERG_PROVIDER=local
OPENAI_BASE_URL=http://127.0.0.1:8080/v1
KONIGSBERG_MODEL=Qwen2.5-Coder-32B-Instruct
```

Optional knobs:

```
# KONIGSBERG_CHEAP_MODEL=Qwen2.5-Coder-32B-Instruct
# KONIGSBERG_LLM_TIMEOUT=600
# KONIGSBERG_MAX_TOKENS=8192
# KONIGSBERG_COMPACT_THRESHOLD=20000
# OPENAI_API_KEY=local
```

| Variable | Meaning |
|---|---|
| `KONIGSBERG_PROVIDER=local` | Force the OpenAI-compat path. Values `local`, `openai`, `llama.cpp`, `llamacpp`, `openai-compat` all select it. |
| `OPENAI_BASE_URL` | llama-server `/v1`. Default if unset and provider is local: `http://127.0.0.1:8080/v1`. |
| `KONIGSBERG_MODEL` | Id sent as `model` (also `OPENAI_MODEL` / `LLAMA_CPP_MODEL`). |
| `KONIGSBERG_CHEAP_MODEL` | Compaction / cheap tier; defaults to the same id as the hunt model. |
| `KONIGSBERG_LLM_TIMEOUT` | HTTP timeout in seconds (default 600). Local 32B tool turns can be slow. |
| `KONIGSBERG_MAX_TOKENS` | Completion cap (default 4096). Raise if the model truncates tool JSON. |
| `KONIGSBERG_COMPACT_THRESHOLD` | Estimated-token trigger to summarize old chat. Local provider defaults to **20000**; Anthropic defaults to 80000. Ledger is never compacted. |

**If you also have `ANTHROPIC_API_KEY` in `.env` or the environment,
`KONIGSBERG_PROVIDER=local` is mandatory.** Otherwise the Anthropic key
wins (so a leftover `OPENAI_BASE_URL` from another project cannot steal
the session — and so you do not accidentally spend 48 hours on Opus).

Provider resolution, in order:

1. `KONIGSBERG_PROVIDER` if set (`anthropic`/`claude` vs `local`/`openai`/…)
2. else `ANTHROPIC_API_KEY` → Claude
3. else a configured OpenAI/llama base URL → local
4. else scripted / offline ( `--forever` refuses to start)

---

## 6. Confirm the interactive banner

```bash
uv run konig
```

You should see something like:

```
formal: ✓ live · empirical: ✓ ready · enum: ✓ geng · model: ✓ Qwen2.5-Coder-32B-Instruct
```

- `formal: ✓ live` — LeanREPL started (`formal/.lake` present).
- `model: ✓ …` — live provider; **not** `offline`.
- `enum: ✓ geng` — nauty found.

`/model list` shows the local catalog; `/model <id>` changes the name sent
to the server. `/help` lists slash commands. `/quit` exits.

If `model:` is offline, `--forever` will refuse: the campaign needs a live
provider.

---

## 7. Smoke the hunt (do this before a long soak)

A capped campaign is the right first test. Twenty rounds is a few minutes
to an hour depending on the GGUF and whether Lean is cold.

```bash
# from repo root; llama-server already up
PYTHONUNBUFFERED=1 KONIGSBERG_PLAIN=1 \
  uv run konig --forever --max-rounds 20
```

`KONIGSBERG_PLAIN=1` disables Rich styling (better for logs).
`PYTHONUNBUFFERED=1` prints tool lines as they happen.

**Healthy smoke**

1. Banner: live Lean + your GGUF id.
2. First turns are **tool calls** (`literature_search`, then Lean or
   `make_graph` / `reducible_configuration`), not a wall of commentary.
3. Native `tool_calls` in the server log is success. Tagged
   `<tool_call>{...}</tool_call>` is the harness fallback (acceptable).
   Markdown-fenced JSON in commentary means `--jinja` is wrong.
4. `#check` of a Literature name (e.g. `BK_ReducibleOfFChoosable.reducible_of_fChoosable`)
   returns a type, not `Unknown identifier`.
5. Process exits 0 at `round cap reached (20/20)` with a session id printed.
6. Ledger may contain `python-checked` graphs and **FORBIDDEN CONFIGURATION**
   claims (conditional on the reducibility bridge). Empty ledger + no tools
   is a failed smoke.

**Unhealthy smoke — fix before `--forever`**

| Symptom | Likely cause |
|---|---|
| `--forever` exits immediately: needs a live model | `.env` not loaded; cwd not repo root; provider still Anthropic-less and no URL |
| Banner shows Opus / Claude | `ANTHROPIC_API_KEY` won; set `KONIGSBERG_PROVIDER=local` |
| `cannot reach LLM at http://127.0.0.1:8080/v1` | llama-server not running, wrong port, or firewall |
| Commentary only, no `⎿` tool lines | missing `--jinja`, base GGUF, or Qwen3 thinking still on |
| `Unknown identifier` on Literature theorems | oleans stale; wait for auto `lake build Konigsberg`, or run it yourself |
| `lean_search` ERROR: tactic must be `#check` | model used the wrong tool; ignore, campaign continues |
| First Lean tool hangs then all Lean fails | REPL timeout killed the process; restart Konigsberg (Lean does not self-heal) |

Note the session id (e.g. `6c30d517b0f3`). Logs live at
`~/.konigsberg/sessions/<id>.jsonl`.

In the REPL, the same cap is not exposed; interactive campaign is
`/forever` (unlimited until settlement or Ctrl-C).

---

## 8. Launch the unbounded BK campaign

When the smoke looks right:

```bash
# tmux recommended
tmux new -s bk
cd /path/to/konigsberg
PYTHONUNBUFFERED=1 KONIGSBERG_PLAIN=1 uv run konig --forever 2>&1 | tee hunt.log
```

Equivalents:

```bash
make campaign                 # uv run konig --forever
uv run konig --forever
```

Detach tmux (`Ctrl-b d`). Reattach with `tmux attach -t bk`.

**Resume after Ctrl-C, a crash, or a capped test**

```bash
uv run konig --continue --forever
uv run konig --resume <session-id> --forever
```

`--continue` loads the latest session under `~/.konigsberg/sessions/`.
Locked lemmas are replayed into a fresh Lean env. The ledger is restored
from recorded Claims, not recomputed.

Override the session directory:

```bash
uv run konig --forever --sessions-dir /path/to/sessions
```

A second capped continuation:

```bash
uv run konig --continue --forever --max-rounds 50
```

`--max-rounds 0` means unlimited (the default for `--forever` when the flag
is omitted).

---

## 9. What to expect over hours (and how a proof lands)

The campaign is instructed to **build on Rabern**, not restart from Brooks:
list bounds, BasicIrreducible, kernel-perfect choosability, 4-list-critical
edge bounds, Ore-Vizing, hitting max cliques, Cranston–Rabern equivalent
conjectures, χ=Δ big cliques, Brooks-and-Beyond list Brooks, and the
reducible-configuration / f-choosability line. Those increments are how a
kernel proof of `borodinKostochka` gets assembled.

The loop carries a **staircase** (not a generic “continue”):
`campaign_status` plus every continue prompt list locked lemmas, distinct
forbidden `core=` strings, and the NEXT increment. First incomplete step,
one per circuit:

1. Re-derive Rabern's seed configs (`campaign_status` names the next un-minted
   seed), then a new core. The reducibility bridge
   `BK.reducible_of_fChoosable` is already **formalized** in Literature — do
   not spend a circuit re-proving it.
2. Propose μ+rules; run `discharging_unavoidable` against ledger 𝒞 (D=9).
   On a MISS, forbid the surviving neighborhood or repair the rules.
3. Durable `lean_prove` of `BK.reducible_and_unavoidable_imp_no_counterexample`,
   then `borodinKostochka_at_nine` (Δ=9 milestone, not halt).
4. Durable `lean_prove` of `borodinKostochka`.

Retesting a listed core is flagged **REDISCOVERY** — that is not progress.
If the stair freezes (same |𝒞|, same durable lemmas, same discharging miss)
the hunt injects **REFORMULATE**: Rabern's move of trading BK for an
a-priori-weaker equivalent (`CranstonRabern_BKEquivalentConjectures` —
χ=Δ=9 ⇒ K₃∗Ē₆ as a subgraph; f-choosable joins excluded from D-critical
graphs). That is where choosability bites. Settlement is still durable
`borodinKostochka`. The banner does not fire while NEXT is still a Rabern
seed or the reducibility bridge.

Typical early Claims (Opus smoke tests looked like this; Qwen will be
noisier):

- `make_graph` of small cores (cycles, bipartite graphs, edge lists).
- `reducible_configuration` **FORBIDDEN** for even cycles as all-low-vertex
  cores at Δ = 9. The bridge `BK.reducible_of_fChoosable` is formalized;
  HITs name H_BK and are not tagged conditional on it. After the first C₄,
  the stair tells the model not to retest it.
- Inconclusive misses (K₂, odd cycles, bad f-lists). A miss proves nothing.
- Occasional failed `lean_prove`. Successes lock `(name, snippet)` on the
  session (`lemma_list` / `/lemmas`) so later rounds can reuse them.

A 27B/32B coder will miss more tools and fail more proofs than a frontier
cloud model. It is still allowed to prove BK: if `lean_prove` returns a
durable kernel Claim for `borodinKostochka`, the campaign stops with
**PROVED**. Clock time without that Claim is not a proof; that Claim is.

**Lean timeout:** if a snippet exceeds the REPL timeout, the Lean process
is **killed**. Empirical tools continue; later `lean_prove` fails until you
restart Konigsberg (`--continue --forever`). Watch for a burst of Lean
errors after a hang.

**Compaction:** local sessions summarize older chat around ~20k estimated
tokens so a 32k llama context does not blow up. Claims stay on the ledger
verbatim.

**`arxiv_search`:** hits the public arXiv API. Everything else in the hunt
is offline. Disable the NIC if you want a hard air gap; the agent can live
on the in-repo corpus.

---

## 10. Stopping, inspecting, promoting

- **Ctrl-C** — interrupt at an event boundary; session is saved.
- Round cap — `round cap reached (N/N)`; session id printed.
- Settlement — `Campaign stopped: Borodin–Kostochka PROVED` means a durable
kernel `lean_prove` of `borodinKostochka` is on the ledger. Inspect that
Claim (`/ledger`, session JSONL) before treating the banner as the last
word — the kernel is the warrant, not the model.

Inspect:

```bash
ls ~/.konigsberg/sessions/
# latest jsonl is the transcript + claims
```

Interactive:

```bash
uv run konig --continue
```

Then `/ledger`, `/lemmas`, `/claim <id>`. Durable kernel proofs can go
through `/referee` and `/promote` into Literature; promotion is
**human-gated** and is not part of `--forever`.

---

## 11. Trust, in one paragraph

The model cannot mint a Claim — tools can. `lean_prove` is the Lean kernel;
a durable kernel proof of `borodinKostochka` **is** a proof of
Borodin–Kostochka, from a local 32B or from Opus. `reducible_configuration`
/ `bk_predicate` are empirical certificates with explicit caveats.
Literature `stated` entries typecheck and may contain `sorry` until
replaced by a kernel proof. `literature` status in `REFERENCES.toml` is
citation only. A long run with no settlement Claim is not a proof; a
finite sweep cannot substitute for that Claim. The campaign exists so the
Claim can appear.

---

## 12. Checklist

- [ ] `uv sync` and `make deps`; `geng` on PATH
- [ ] `cd formal && lake exe cache get && lake build`
- [ ] `make lean-smoke`
- [ ] llama-server with `--jinja`, `--ctx-size 32768`, thinking off
- [ ] `curl -s http://127.0.0.1:8080/v1/models` succeeds
- [ ] `cp .env.example .env` with `KONIGSBERG_PROVIDER=local` and `OPENAI_BASE_URL=…/v1`
- [ ] `uv run konig` banner: `formal: ✓ live` and your GGUF, not `offline`
- [ ] `--forever --max-rounds 20` shows tool calls and a session id
- [ ] only then `uv run konig --forever` under tmux + `tee`

---

## Command cheat sheet

```bash
uv run konig                              # interactive REPL
uv run konig --forever                    # BK campaign (unlimited)
uv run konig --forever --max-rounds 20    # capped smoke
uv run konig --continue --forever         # resume latest
uv run konig --resume ID --forever        # resume that session
make campaign                             # same as --forever
make deps                                 # python + nauty
make lean-setup                           # lake update + cache + build
make lean-smoke
make gates                                # trust gates (no Lean build)
```
