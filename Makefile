# Makefile: short names for the commands this project runs.
# Why: one habit (make test, make lint) instead of remembering uv invocations.
# eval and bank are placeholders until those steps are built. report scores the two saved Phase 0
# runs below (no API call), compares them and writes phase0_resolvability/report.md.
# Run: make test | make lint | make report [BEFORE_RUN=<run_id> AFTER_RUN=<run_id>] | make eval | make bank

.PHONY: test lint report eval bank

# Prompt v1 and prompt v3 on the TEST slice (v2 was only run on DEV).
BEFORE_RUN ?= 20261101T084927Z_v1_test
AFTER_RUN ?= 20261101T103105Z_v3_test

test:
	uv run pytest

lint:
	uv run ruff check .

report:
	uv run python -m phase0_resolvability.evaluate $(BEFORE_RUN)
	uv run python -m phase0_resolvability.evaluate $(AFTER_RUN)
	uv run python -m phase0_resolvability.compare $(BEFORE_RUN) $(AFTER_RUN)
	uv run python -m phase0_resolvability.make_report $(BEFORE_RUN) $(AFTER_RUN)

eval:
	@echo not built yet

bank:
	@echo not built yet
