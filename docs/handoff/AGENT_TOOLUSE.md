# Switch the loop to native tool use (Cursor spec)

*Replace the text-JSON action protocol with the Anthropic API's native tool use.
Today the model types a JSON action into a chat message and `_parse_action` reads
it back; a live run just failed on turn 1 because the model wrapped the call in
prose + a ```` ```json ```` fence. Native tool use makes that whole failure class
impossible: the model returns a structured tool call whose args are already a
validated dict — nothing to strip, nothing to `json.loads`, nothing to guess.*

This is the standard, correct way to build an agent on the Anthropic API (the
same `tool_use`/`tool_result` primitive every real harness uses). The current
text protocol was a fine bootstrap — it proved the trust chain end to end — and
this is the "now make it real" step, deliberately scoped small.

**The trust invariant is unchanged and load-bearing:** only a tool-minted `Claim`
enters the ledger; a model that merely *asserts* a result mints nothing
(`test_agent.py::test_lying_final_mints_nothing`). Nothing here weakens that — a
structured final turn is still just text.

---

## What changes (three seams)

1. the `Model` boundary — from "text in, text out" to "conversation + tool
   schemas in, a structured turn out";
2. the registry — each tool gains a pydantic args model; `dispatch` validates
   before calling;
3. the loop — thread `tool_use` → run tool → `tool_result`, instead of parse.

Provider-agnosticism is preserved by normalizing the model turn behind our own
dataclasses; the loop and tests never touch the Anthropic block shape.

---

## WP1 — Normalized model boundary (`models.py`)

Add small provider-neutral turn types (new `models.py` types, or a
`harness/konigsberg_harness/messages.py`):

```python
@dataclass(frozen=True)
class ToolCall:      # the model wants to run a tool
    id: str          # provider-issued id; echoed back in the result
    name: str
    args: dict

@dataclass(frozen=True)
class ToolResultMsg: # our reply to a ToolCall
    id: str
    content: str
    is_error: bool = False

@dataclass(frozen=True)
class UserMsg:  text: str
@dataclass(frozen=True)
class AssistantText:  text: str   # a plain (final) turn, no tool call
```

Extend the `Model` protocol with a tool-aware method (keep `complete` if other
callers use it; the loop stops using it):

```python
def respond(
    self,
    history: list[UserMsg | ToolCall | ToolResultMsg | AssistantText],
    tools: list[dict],          # [{name, description, input_schema}], from the registry
    *, tier: Tier,
) -> list[ToolCall] | AssistantText: ...
```

- Returns **a list of `ToolCall`** when the model wants to act (Anthropic can emit
  several `tool_use` blocks in one turn — return all of them), or **`AssistantText`**
  when it stops (`stop_reason != "tool_use"`).

**`AnthropicModel.respond`:**
- translate `history` → Anthropic `messages` (a `ToolCall` becomes an assistant
  message with a `tool_use` block; a `ToolResultMsg` becomes a user message with a
  `tool_result` block carrying the matching `tool_use_id` and `is_error`);
- pass `tools=tools` and `max_tokens`; leave `tool_choice` on auto;
- on `stop_reason == "tool_use"`, collect every `tool_use` block → `list[ToolCall]`
  (id, name, `input` dict); otherwise concatenate text → `AssistantText`.
- Key/lazy-import/tier→id map are already correct — reuse them.

**Tests (`tests/test_models.py`, no network):** monkeypatch the client to return a
fake message with (a) one `tool_use` block → assert one `ToolCall` with parsed
args, (b) multiple `tool_use` blocks → assert all returned, (c) a text-only stop →
assert `AssistantText`, (d) missing key still raises. Keep the optional live smoke.

---

## WP2 — Pydantic arg models + validate-then-dispatch (`tools/`)

One pydantic model per model-callable tool = single source of truth for its args:
it generates the API `input_schema` **and** validates what comes back.

- `Tool` gains `args_model: type[BaseModel] | None = None`.
- `register(name, fn, doc, args_model=None)`.
- `tool_specs() -> list[dict]`: `{"name", "description": doc,
  "input_schema": args_model.model_json_schema() if args_model else
  {"type":"object","properties":{}}}`. (This replaces/augments `spec()`.)
- `dispatch(name, args: dict)`: if `args_model` is set,
  `validated = args_model.model_validate(args)` then `fn(**validated.model_dump())`;
  else `fn(**args)`. A `pydantic.ValidationError` is caught by the loop and fed
  back as an error `tool_result` (the model can correct itself) — **not** a crash.

Define arg models for the model-callable tools in `build_registry`:
`choosability_refute(graph6:str, k:int, palette:int|None=None)`,
`alon_tarsi(graph6:str)`, `fixer_breaker(graph6:str, sizes:list[int])`,
`verify_coloring(graph6:str, coloring:list[int])`,
`lean_check/lean_typecheck_statement/lean_search/lean_prove` (their snippet/goal
strings). `counterexample_search` stays code-only (non-serializable predicate) —
do not expose it with a schema.

Add `pydantic` to the harness deps if not already present.

---

## WP3 — Loop threads tool_use/tool_result (`agent.py`)

Replace `_parse_action` + the string prompt with a message loop:

- Seed `history = [UserMsg(<task + brief instructions>)]`. The tool list is passed
  structurally via `tools=`, so the old "respond with ONE JSON object" prompt text
  goes away.
- Each step: `turn = model.respond(history, registry.tool_specs(), tier=FRONTIER)`.
  - `AssistantText` → `final = turn.text`; break.
  - `list[ToolCall]` → **for every** call in the list (append the whole assistant
    turn to `history` first): `dispatch(name, args)`; build a `ToolResultMsg`
    (rendered result, or `is_error=True` for a `ValidationError`/tool exception);
    append it to `history`. If the result is a `Claim`, `ledger.record(it)`.
    **Every `ToolCall` in a turn must get a matching `ToolResultMsg`** before the
    next `respond` (the API rejects a turn with an unanswered `tool_use`).
- Keep `max_steps`, the `Observation` transcript, and `AgentResult` shape.

**Delete** `_parse_action` and its four tests. The recovery behavior they covered
(malformed action → error observation → continue) is now covered by the
validation-error path, so add a test: a `ToolCall` with bad args produces an error
`tool_result` and the loop continues.

---

## WP4 — Fake model + tests

- `ScriptedModel` now queues normalized turns (`ToolCall(...)` / `AssistantText(...)`)
  instead of JSON strings, and records the `history` it was handed.
- Rewrite `test_agent.py` around it. **Preserve** `test_lying_final_mints_nothing`
  (an `AssistantText` final mints nothing) and
  `test_claim_trust_root_is_stamped_by_tool_not_model` verbatim in intent.
- Update `test_registry.py` for `tool_specs()` (assert each model-callable tool
  carries a JSON-schema with its expected properties) and the `args`-dict dispatch
  signature.
- Update `scripts/agent_demo.py` and `test_agent_e2e.py` to the new fake/turn
  shape. The demo should still show: real `AnthropicModel` if a key is present,
  scripted fake otherwise; end with `verify_coloring` minting a `proved` Claim.

---

## Acceptance

- Model returns structured `ToolCall`s; no JSON-from-text parsing anywhere
  (`_parse_action` gone).
- Each model-callable tool has a pydantic args model; `dispatch` validates and a
  bad-args call becomes an error `tool_result`, not a crash.
- Every `tool_use` in a turn is answered with a `tool_result` (multi-call safe).
- Trust invariant test still passes; `agent_demo` runs offline (scripted) and live
  (with a key).
- `ruff` clean, `uv run pytest` green.

## Scope discipline (don't overreach)

- Provider stays behind the normalized `Model` boundary — the loop and all tests
  remain provider-agnostic (no Anthropic block types leak past `AnthropicModel`).
- **Out of scope:** streaming, parallel tool execution, retry/backoff, prompt
  caching, context-window management. Single call per step; run tool calls
  sequentially. Add those only when measurably justified.
- `tier` stays a per-call arg; no routing DSL.
- Model IDs stay config, not constants.
