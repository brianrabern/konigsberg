.PHONY: gates test lint sync lean-setup lean-smoke axioms-lean

sync:        ## install python packages (editable)
	uv sync

gates:       ## run the trust gates (no Lean build needed)
	python ci/check_status.py formal
	python ci/check_no_sorry.py formal
	python ci/check_axioms.py formal

test: sync   ## run python tests
	uv run pytest

lint: sync   ## ruff
	uv run ruff check .

lean-setup:  ## M0: fetch mathlib + prebuilt oleans + repl, then build
	cd formal && lake update && lake exe cache get && lake build

lean-smoke: sync  ## M0: verify the Lean env round-trips through the REPL
	uv run python scripts/smoke_lean.py

axioms-lean: sync  ## authoritative axiom gate against a live Lean env
	uv run python ci/check_axioms.py formal --run-lean
