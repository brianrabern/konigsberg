# Local LLM — llama.cpp (ROCm) + Qwen 27B/32B

**Operator guide (clone, Lean, `.env`, capped smoke, `--forever` soak):**
[`docs/LOCAL_BK_HUNT.md`](../LOCAL_BK_HUNT.md).

The local model proves BK the same way any model does: it calls `lean_prove`
on `borodinKostochka` and the kernel accepts. It cannot mint a Claim in
prose; tools mint. Weak tool-calling means a worse hunt, not a weaker
ledger.

## llama-server

Instruct/Coder GGUF, `--jinja`, `--ctx-size 32768`, Qwen3 thinking off:

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

```
KONIGSBERG_PROVIDER=local
OPENAI_BASE_URL=http://127.0.0.1:8080/v1
KONIGSBERG_MODEL=Qwen2.5-Coder-32B-Instruct
```

If `ANTHROPIC_API_KEY` is also set, `KONIGSBERG_PROVIDER=local` is required
or Claude wins. 27B/32B coder is the floor for this harness.
