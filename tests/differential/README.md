# Differential tests

Feed nauty-generated graphs to both the .NET oracle (`vendor/`) and the Python
reimplementation; assert identical output. Once the retirement bar is met, the
oracle is deleted and these pin against recorded fixtures.

- `fixtures/` — recorded oracle outputs (tracked), created before `vendor/` dies.
- Also home the bridge round-trip property test (Python graph -> Lean -> back).
