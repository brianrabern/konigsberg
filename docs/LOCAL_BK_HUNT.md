# Clone, install, run with llama.cpp (ROCm) + Qwen

One path. No cloud key. From an empty machine with an AMD GPU to
`uv run konig --forever`.

The campaign is the Borodin–Kostochka hunt. It stops on a durable Lean
kernel proof of `borodinKostochka`, a certified Δ ≥ 9 counterexample, or
you. Model prose never counts.

---

## 0. Once, on the machine

You need Git, Python ≥ 3.11, a C++ toolchain, CMake, working **ROCm**
(`rocminfo` lists your GPU), **24 GB+ VRAM** for a 32B Q4 GGUF (48 GB is
comfortable), and ~25 GB disk for mathlib cache + the GGUF.

```bash
# uv — https://docs.astral.sh/uv/
curl -LsSf https://astral.sh/uv/install.sh | sh

# Lean toolchain manager — pin is formal/lean-toolchain (v4.31.0)
curl https://elan.lean-lang.org/elan-init.sh -sSf | sh
source "$HOME/.elan/env"   # or restart the shell
```

**llama.cpp with HIP (ROCm).** The old `LLAMA_HIPBLAS` flag is ignored and
gives a CPU-only binary. Use `GGML_HIP=ON`. Omit `GPU_TARGETS` to compile
for the GPU in this machine, or set it from `rocminfo` (`gfx1100`,
`gfx1030`, …).

```bash
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp
HIPCXX="$(hipconfig -l)/clang" HIP_PATH="$(hipconfig -R)" \
  cmake -S . -B build -DGGML_HIP=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j"$(nproc)"
# binary: ./build/bin/llama-server
```

Put `llama-server` on `PATH`, or call it by full path below.

**Qwen GGUF** — Instruct/Coder, not a base checkpoint. Default this guide
uses:

- [Qwen2.5-Coder-32B-Instruct GGUF](https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct-GGUF),
  `Q4_K_M` (or `Q5_K_M` if VRAM allows)

Qwen3-Coder 32B / 30B-A3B also works. 8B-class models will demo the CLI
and miss tools; they are not a hunt engine.

---

## 1. Clone Konigsberg

```bash
git clone https://github.com/brianrabern/konigsberg.git
cd konigsberg
```

Stay in the **repository root** for `make`, `uv run konig`, and `.env`.

---

## 2. Install this repo

```bash
make setup          # python (uv sync) + nauty + mathlib oleans + lake build
make lean-smoke     # LeanREPL round-trip; should print OK
```

`make setup` is `make deps` then `make lean-setup`. Do **not** compile
mathlib from source; `lake exe cache get` uses the official cache.

If nauty/`geng` is missing and you are not on brew/apt/dnf/pacman, install
it yourself. The hunt still runs without `geng` (named graphs + Lean);
enumeration tools degrade.

---

## 3. Start llama-server (leave it running)

Required flags: `--jinja` (native tools; without it Qwen dumps XML),
`--ctx-size 32768`, thinking off (Qwen3). `-ngl 99` offloads every layer.

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

Startup log must name the **HIP/ROCm** backend and offloaded layers. A
HIP build that fell back to CPU still answers, slowly — check `rocm-smi`.

```bash
curl -s http://127.0.0.1:8080/v1/models    # JSON list, not a connection error
```

---

## 4. Point Konigsberg at the server

```bash
cp .env.example .env
# edit KONIGSBERG_MODEL if your GGUF name differs
```

`.env` is gitignored. The CLI loads it at startup; shell exports win.

```
KONIGSBERG_PROVIDER=local
OPENAI_BASE_URL=http://127.0.0.1:8080/v1
KONIGSBERG_MODEL=Qwen2.5-Coder-32B-Instruct
```

If `ANTHROPIC_API_KEY` is also set, `KONIGSBERG_PROVIDER=local` is
mandatory or Claude wins.

---

## 5. Banner, then a 20-round smoke

```bash
uv run konig
```

You want `formal: ✓ live` and `model: ✓ Qwen…`, not `offline`. `/quit`
exits. Then:

```bash
PYTHONUNBUFFERED=1 KONIGSBERG_PLAIN=1 \
  uv run konig --forever --max-rounds 20
```

Healthy: tool calls in the first turns (`literature_search`,
`make_graph`, `reducible_configuration`, Lean), exit 0 at
`round cap reached (20/20)`, a session id. Empty ledger and no tools is a
failed smoke — fix the table below before an unbounded run.

---

## 6. Pre-flight before the unbounded soak

The 20-round smoke is not enough. Before `tmux` / `--forever` with no round
cap:

```bash
make preflight
```

That is `cd formal && lake build` then `make gates` (green). Gates already
run `ci/discharging_self_test.py`. To smoke discharging on its own:

```bash
uv run python ci/discharging_self_test.py
```

**Retro-`/referee` the reducibility bridge** — still ungated. The lemma is
already `formalized` as
`Konigsberg.Literature.Coloring.BK_ReducibleOfFChoosable.reducible_of_fChoosable`.
`ci/referee_self_test.py` (in gates) is the planted-flaw fixture, not a
review of this theorem. `/promote` stays human-gated.

```bash
uv run python scripts/referee_bridge.py
```

Needs a live model for an adversarial pass (same `.env` as the hunt).
Without one you only get heuristic checks. Do **not** `/promote` — the
corpus already has the entry.

---

## 7. Unbounded campaign

```bash
tmux new -s bk
cd /path/to/konigsberg
PYTHONUNBUFFERED=1 KONIGSBERG_PLAIN=1 uv run konig --forever 2>&1 | tee hunt.log
```

Detach with `Ctrl-b d`. Resume after Ctrl-C or a crash:

```bash
uv run konig --continue --forever
```

---

## If something breaks

| Symptom | Fix |
|---|---|
| `--forever` exits: needs a live model | cwd is repo root; `.env` exists; llama-server up |
| Banner shows Claude / Opus | `KONIGSBERG_PROVIDER=local` in `.env` |
| cannot reach `127.0.0.1:8080` | server not running, wrong port |
| Commentary only, no tool lines | missing `--jinja`, or a base (non-Instruct) GGUF |
| llama-server is slow, `rocm-smi` idle | CPU-only binary; rebuild with `GGML_HIP=ON` |
| `Unknown identifier` on Literature names | `make lean-setup` (oleans stale) |
| First Lean tool hangs, then all Lean fails | REPL timeout killed Lean; `--continue --forever` |

Do not build `vendor/` — that is a test oracle. Differential tests skip
if it is missing.

---

## What `--forever` is doing

Tools mint Claims; the model only proposes calls. Progress is locked
lemmas, new forbidden cores, and kernel subproofs. A long run with no
settlement Claim is unfinished work, not a broken install.

`campaign_status` names the next increment. Retesting a listed core is
**REDISCOVERY**. A frozen stair injects **REFORMULATE** (equivalent
weaker-looking BK forms). Settlement is still durable `borodinKostochka`.

`--until-proved` stops on the first successful `lean_prove`. Do not use
it for this campaign.

Sessions live in `~/.konigsberg/sessions/`. Trust model:
[`TRUST.md`](TRUST.md). `docs/handoff/` is a lab notebook — ignore it
unless you are debugging an ingest.

---

## Cheat sheet

```bash
make setup                                # python + nauty + Lean
make lean-smoke
cp .env.example .env
uv run konig                              # interactive
uv run konig --forever --max-rounds 20    # smoke
make preflight                            # lake build + gates before soak
uv run python ci/discharging_self_test.py # discharging smoke (also in gates)
uv run python scripts/referee_bridge.py   # retro-referee the bridge (ungated)
uv run konig --forever                    # campaign
uv run konig --continue --forever         # resume
make campaign                             # same as --forever
make gates                                # CI trust gates (no Lean build)
```
