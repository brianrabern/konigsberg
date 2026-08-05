# Differential tests

Feed shared inputs to the .NET oracle (`vendor/choosability-oracle/`) and the
Python FixerBreaker port; assert identical `total_boards` / `win` / `nearly_win`.

- `fixtures/fixer_breaker_corpus.jsonl` — recorded oracle outputs (committed).
  CI runs against this file with **no dotnet**.
- `gen_oracle_cases.py` — regenerate the corpus (needs `dotnet` + a built oracle).
  Hard-gates on `oracle --selftest` before writing.

See `docs/handoff/WP_C_ORACLE.md` and `vendor/choosability-oracle/README.md`.
