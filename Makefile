# Makefile: short names for the commands this project runs.
# Why: one habit (make test, make lint) instead of remembering uv invocations.
# eval and bank are placeholders until those steps are built. For now report only
# scores the latest Phase 0 run (summary.md and confusion.csv in its results folder).
# Run: make test | make lint | make report | make eval | make bank

.PHONY: test lint report eval bank

test:
	uv run pytest

lint:
	uv run ruff check .

report:
	uv run python -m phase0_resolvability.evaluate --latest

eval:
	@echo not built yet

bank:
	@echo not built yet
