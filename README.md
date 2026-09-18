# Konigsberg

Formal and empirical tools for graph theory research. The LLM proposes; **tools
mint Claims** on an epistemic ledger. Lean kernel proofs and solver certificates
are established; model prose is commentary.

The standing target is the Borodin–Kostochka conjecture (χ ≤ max{Δ−1, ω} for
Δ ≥ 9). Graph coloring is the first vertical.

## Modes

Same REPL, same ledger. What changes is when the loop stops.

| Mode | How | Stops when |
|---|---|---|
| **Chat** (default) | `uv run konig` | First prose reply, or ~40 tool steps. You steer. |
| **Hunt** | `uv run konig --until-proved --task "…"` or `/hunt <goal>` | A `lean_prove` kernel proof of that goal (or Ctrl-C / round cap). Prose does not stop it. |
| **Forever** | `uv run konig --forever` or `/forever` | Durable `lean_prove` of `borodinKostochka`, a certified Δ ≥ 9 `bk_predicate` **VIOLATES**, or you. Ordinary lemmas lock and the campaign continues. |

`--until-proved` is for a named lemma. `--forever` is the BK campaign. Do not
mix them up.

Sessions persist under `~/.konigsberg/sessions/`. Resume with `--continue` or
`--resume <id>` (add `--forever` / `--until-proved` to keep hunting).

## Run on a local LLM (llama.cpp + ROCm + Qwen)

Walkthrough: [`docs/LOCAL_BK_HUNT.md`](docs/LOCAL_BK_HUNT.md).

```bash
git clone https://github.com/brianrabern/konigsberg.git && cd konigsberg
make setup                 # python, nauty, mathlib cache, lake build
make lean-smoke
cp .env.example .env       # local provider → llama-server :8080
# llama-server already up (HIP build, --jinja, ctx 32k, Qwen Instruct GGUF)
uv run konig                             # chat
uv run konig --forever --max-rounds 20   # smoke the campaign
uv run konig --forever                   # unbounded BK hunt
```

Needs [`uv`](https://docs.astral.sh/uv/), [`elan`](https://github.com/leanprover/elan),
llama.cpp built with **`GGML_HIP=ON`**, and a Qwen Instruct/Coder GGUF. No
Anthropic key. `make setup` does not rebuild mathlib from source.

Claude instead: set `ANTHROPIC_API_KEY` in `.env` (and omit
`KONIGSBERG_PROVIDER=local`). Same commands.

```bash
uv run konig --until-proved --task "Prove Nat.add_comm for 0"
make gates                   # CI trust gates
```

## Layout

Three tiers. Lean and Python never import each other; the harness talks to both
via subprocess.

| Path | What |
|---|---|
| `formal/` | Lean 4.31 + mathlib + Konigsberg library + Literature corpus |
| `empirical/` | Graphs, choosability, reducible configs, discharging |
| `harness/` | Agent loop, tools, ledger, REPL |
| `ci/` | Trust gates (axioms, sorry, imports, …) |
| `vendor/` | .NET test oracle — skip; the hunt does not need it |
| `templates/` | Skeletons for new areas / literature entries |

## Trust

Only a tool-minted **Claim** is established. Chat answers are zoned
`Established (ledger)` vs `Commentary`. Details: [`docs/TRUST.md`](docs/TRUST.md).
`docs/handoff/` is a lab notebook.

| Label | Means |
|---|---|
| `proved` | Lean kernel, axioms in whitelist |
| `certificate-checked` | Finite object independently re-checked |
| `solver-certified` | Solver asserted; port matches oracle. Not re-checked |
| `python-checked` | Enumeration up to a stated bound |
| `stated` | Typechecks. Says nothing about truth |

`/promote` into Literature is human-gated. A finite sweep does not prove BK.

## License

Apache License 2.0. See `LICENSE`.
