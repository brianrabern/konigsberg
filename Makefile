.PHONY: gates test lint sync lean-setup

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

lean-setup:  ## M0: fetch mathlib + prebuilt oleans, then build
	cd formal && lake update && lake exe cache get && lake build
