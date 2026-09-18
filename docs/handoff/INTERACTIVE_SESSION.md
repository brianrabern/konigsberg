# Interactive session — a Claude-Code-shaped REPL for Konigsberg (Cursor spec)

*Turn the loop from a closed `run(task) -> result` function into an interactive
session: a CLI REPL where you give a task, watch the agent call tools live, steer
or interrupt mid-investigation, and have the conversation + ledger persist and
resume. This is the piece that makes Konigsberg an instrument you converse with,
not a batch job you fire.*

This spec deliberately mirrors Claude Code's known design. The mapping is explicit
so we copy what's proven and don't reinvent it. Where Konigsberg differs from
Claude Code, it's for a principled reason (the ledger), noted inline.

## How Claude Code works → how Konigsberg should

| Claude Code | Konigsberg analogue |
|---|---|
| Single-threaded **master loop**; no multi-agent graph | Keep the single `Agent` loop we have. Do **not** add orchestration/subagents in v1. |
| **The loop closes on *context assembly*, not the model call** — every iteration rebuilds the context sent to the model | Refactor so each turn re-assembles the message context from session state (history + tool schemas), rather than the model owning any state. |
| Native `tool_use` / `tool_result` turns | Already done (`AGENT_TOOLUSE.md`). Build on it. |
| **Compaction pipeline**: near the context limit, summarize older history, keep recent exchanges + key decisions | Compact the *chat transcript* when it nears the model's context window — but **never compact the ledger**. The ledger *is* Konigsberg's "key decisions kept intact," and it's mechanically-stamped trust state, not a lossy summary. This is the one place we improve on CC's design, not copy it. |
| **Real-time steering** via an async input queue; interrupt any time to redirect | v1: turn-boundary steering + a clean interrupt (below). Full mid-tool-call injection is CC's sophistication — note it, defer it. |
| **Session persistence**: every message/tool-use/result saved as JSONL under `~/.claude/projects/`; enables `--resume`/`--continue` | A `SessionStore` writing JSONL (messages + tool calls + ledger claims) under `~/.konigsberg/sessions/<id>.jsonl`; `--resume <id>` / `--continue`. |
| **Slash commands** (`/compact`, `/clear`, `/resume`, …) | A small built-in set (below). |
| Interactive CLI **and** headless (`-p`) modes | Interactive REPL now; keep a one-shot `--task` headless path (the current `agent_demo` behavior) working. |
| Permission system gating side-effecting tools | Konigsberg tools are **safe** (solvers, Lean checks — no side effects), so no per-tool approval. Optional "this may be slow" heads-up only. Don't build CC's permission system. |

---

## WP1 — Session state + persistence (`session.py`)

The durable object the REPL drives. This is the "persistence" gap and the REPL's
backbone.

- **`Session`**: holds `id`, the normalized message `history` (the `UserMsg` /
  `ToolCall` / `ToolResultMsg` / `AssistantText` types from `AGENT_TOOLUSE.md`),
  and the `Ledger`. One `Session` = one investigation.
- **`SessionStore`** (JSONL, mirroring CC): append every event —
  user message, assistant turn, each tool call, each tool result, each minted
  Claim — as one JSON line under `~/.konigsberg/sessions/<id>.jsonl`. Append-only
  is what later makes resume/rewind possible.
- **Resume/continue**: `load(id)` replays the JSONL to reconstruct `history` +
  `Ledger`; `latest()` for `--continue`. The **ledger is reconstructed from its
  recorded claims, never re-derived** — a resumed session inherits exactly the
  trust state it had, no re-running of solvers/Lean.
- Tests: round-trip a session (write → load → identical history + ledger);
  resuming preserves claim trust roots.

## WP2 — Loop as an event-emitting, driveable turn (`agent.py`)

Refactor `Agent` so the REPL can drive it and render progress, per CC's
"loop closes on context assembly."

- Split the monolithic `run()`:
  - `step(session) -> AgentEvent`-stream (a generator/callback): re-assemble
    context from `session.history` + `registry.tool_specs()`, call
    `model.respond(...)`, and **yield events as they happen** — `ToolCallProposed`,
    `ToolResult`, `ClaimMinted`, `AssistantFinal`. The REPL renders each event
    live (this is the cheap "streaming": print tool activity as it occurs; token
    streaming is later polish).
  - Each tool call/result/claim is appended to `session` (and the store) as it
    happens, so an interrupt never loses work.
- Keep the **trust invariant** exactly: only a `Claim` tool result is recorded;
  an `AssistantFinal` mints nothing. The existing invariant tests must still pass.
- `run(task)` becomes a thin wrapper over `step` for the headless path.

## WP3 — Context compaction (`compaction.py`)

CC's compaction, adapted so it can never touch trust state.

- Track an approximate token count of `session.history`. When it crosses a
  threshold (e.g. a configurable fraction of the model's context window),
  **compact**: replace older transcript turns with a single summary `UserMsg`
  ("Summary of earlier work: …"), keeping the most recent N turns verbatim — CC's
  "structured extraction + keep recent exchanges."
- Produce the summary with the **CHEAP tier** (it's summarization, not proof
  search — exactly CC's split).
- **Invariant: compaction only ever rewrites the chat transcript. The `Ledger` is
  untouched.** Established claims survive verbatim; the model always sees the full
  current trust state even after older *chat* is compacted. Add a test asserting
  the ledger is byte-identical across a compaction.
- Expose it as `/compact` (manual) and an auto-trigger at the threshold.

## WP4 — Steering & interrupt (`repl.py`)

- **Interrupt**: `Ctrl-C` during an agent run halts cleanly at the next event
  boundary, flushes state to the store, and returns to the prompt with the
  session intact (never a half-written turn, never a crash). This is the
  load-bearing steering primitive for v1.
- **Turn-boundary steering**: after the agent yields `AssistantFinal` (or is
  interrupted), the human's next message is just appended to `history` and the
  loop continues — the conversation accumulates. This gets ~80% of CC's
  redirect-without-restart with none of the async-queue machinery.
- Note (defer): CC injects instructions *mid-tool-call* via an async dual-buffer
  queue. Out of scope for v1; leave a comment marking where it would hook in.

## WP5 — The REPL + slash commands (`repl.py`, `scripts/konigsberg` entry point)

- A readline prompt loop: read a line → if it starts with `/`, handle as a command
  → else treat as a user message and run `Agent.step`, rendering events live →
  back to the prompt. Persist after every turn.
- Built-in slash commands (small, CC-shaped):
  - `/help` — list commands and registered tools.
  - `/tools` — show the tool registry (name + doc + arg schema).
  - `/ledger` — print current claims with their trust roots. (Konigsberg-specific;
    this is the payoff of the whole trust model — make it a first-class view.)
  - `/compact` — force compaction now.
  - `/clear` — start a fresh session (new id).
  - `/resume [id]`, `/save` — session lifecycle over `SessionStore`.
  - `/quit`.
- CLI flags on the entry point: `--task "<t>"` (headless one-shot, prints ledger,
  exits — preserves current `agent_demo` behavior), `--resume <id>`, `--continue`,
  `--model`/tier overrides already handled by `models.py`.
- Real live model when `OPENAI_BASE_URL` / `KONIGSBERG_PROVIDER=local` (llama.cpp)
  or `ANTHROPIC_API_KEY` is set; scripted fake otherwise (so the REPL is
  demoable and testable offline). See `docs/handoff/LOCAL_LLM.md`.

## WP6 — Tests

- `SessionStore` round-trip + resume preserves ledger/trust roots (WP1).
- `Agent.step` emits the expected event sequence for a scripted tool→final run;
  interrupt after a tool call leaves a consistent, resumable session (WP2/WP4).
- Compaction shrinks the transcript, keeps the last N turns, and leaves the ledger
  byte-identical (WP3) — the load-bearing compaction test.
- Trust invariant still holds end to end through the REPL path
  (`test_lying_final_mints_nothing` analogue at the session level).
- A slash-command smoke test (`/ledger`, `/tools`, `/compact`) with the fake model.

---

## Acceptance

- `konigsberg` starts an interactive REPL; a task runs with tool activity printed
  live; `Ctrl-C` interrupts cleanly; the next message continues the same session.
- Sessions persist to JSONL and `--resume`/`--continue` restore history **and**
  the exact ledger.
- Auto- and manual compaction work and provably never alter the ledger.
- Headless `--task` one-shot still works; trust invariant tests green;
  `ruff` clean, `uv run pytest` green.

## Scope discipline (copy CC's simplicity, not its surface area)

- **One loop.** No subagents, no orchestration graph, no hooks — CC's own core is
  a single master loop; keep ours single too.
- **No permission system.** Tools are side-effect-free; don't build approval flows.
- **Steering v1 = interrupt + turn-boundary messages.** Defer the async
  mid-tool-call injection.
- **Streaming v1 = print events as they occur.** Token streaming is later.
- **Compaction never touches the ledger.** This is the one non-negotiable
  Konigsberg-specific invariant.
- Provider stays behind `Model`; the REPL depends on `Session`/`Agent`, not on any
  SDK.

## Sources (Claude Code design this mirrors)

- [How Claude Code works — Claude Code Docs](https://code.claude.com/docs/en/how-claude-code-works)
- [How the agent loop works — Claude API Docs](https://platform.claude.com/docs/en/agent-sdk/agent-loop)
- [Claude Code Agent Architecture: Single-Threaded Master Loop (ZenML)](https://www.zenml.io/llmops-database/claude-code-agent-architecture-single-threaded-master-loop-for-autonomous-coding)
- [Claude Code CLI: Session & Context Management](https://admantium.medium.com/claude-code-cli-session-context-management-6a45b120a77f)
- [Mastering Claude Code Sessions: --continue & --resume](https://aiopsschool.com/blog/mastering-claude-code-sessions-continue-resume/)
