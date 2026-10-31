# Makefile: short names for the commands this project runs.
# Why: one habit (make test, make lint) instead of remembering uv invocations.
# report, eval and bank are placeholders until those steps are built.
# Run: make test | make lint | make report | make eval | make bank

.PHONY: test lint report eval bank

test:
	uv run pytest

lint:
	uv run ruff check .

report:
	@echo not built yet

eval:
	@echo not built yet

bank:
	@echo not built yet
