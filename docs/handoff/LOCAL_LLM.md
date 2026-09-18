# Local LLM — llama.cpp (ROCm) + Qwen

Clone → install → server → 20-round smoke → `make preflight` → `--forever`:
[`docs/LOCAL_BK_HUNT.md`](../LOCAL_BK_HUNT.md).

HIP build (not the ignored `LLAMA_HIPBLAS` flag):

```bash
HIPCXX="$(hipconfig -l)/clang" HIP_PATH="$(hipconfig -R)" \
  cmake -S . -B build -DGGML_HIP=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j"$(nproc)"
```

```bash
llama-server \
  -m /path/to/Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf \
  --host 127.0.0.1 --port 8080 \
  --ctx-size 32768 --jinja \
  --chat-template-kwargs '{"enable_thinking": false}' \
  -ngl 99
```
