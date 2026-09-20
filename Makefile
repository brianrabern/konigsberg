.PHONY: gates test lint sync deps setup lean-setup lean-smoke axioms-lean campaign preflight watch

sync:        ## install python packages (editable)
	uv sync

deps:        ## python (uv sync) + system nauty/geng when missing
	uv run python scripts/ensure_deps.py --yes

setup: deps lean-setup  ## clone-to-ready: python + nauty + mathlib cache + lake build

gates: sync  ## run the trust gates (no Lean build needed)
	uv run python ci/self_test_audit.py
	uv run python ci/referee_self_test.py
	uv run python ci/reduction_self_test.py
	uv run python ci/discharging_self_test.py
	uv run python ci/discharging_search_self_test.py
	uv run python ci/check_status.py formal
	uv run python ci/check_no_sorry.py formal
	uv run python ci/check_axioms.py formal
	uv run python ci/check_imports.py formal
	uv run python ci/check_conventions.py formal

test: sync   ## run python tests
	uv run pytest

lint: sync   ## ruff
	uv run ruff check .

lean-setup:  ## mathlib oleans from cache + lake build (uses committed lake-manifest)
	cd formal && lake exe cache get && lake build

lean-smoke: sync  ## M0: verify the Lean env round-trips through the REPL
	uv run python scripts/smoke_lean.py

axioms-lean: sync  ## authoritative axiom gate against a live Lean env
	uv run python ci/check_axioms.py formal --run-lean

campaign:  ## autonomous BK hunt until proved/disproved (needs a live model)
	uv run konig --forever

watch:  ## live progress dashboard for the running hunt (read-only; ARGS=... to pass flags)
	uv run python scripts/hunt_watch.py $(ARGS)

preflight:  ## lake build + trust gates before an unbounded --forever soak
	cd formal && lake build
	$(MAKE) gates
