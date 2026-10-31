# config.py: the one place that reads .env and names the Claude models.
# Why: model IDs and secrets must not be scattered through the code (CLAUDE.md).
# Model IDs checked against the Claude docs Models overview on 2026-10-31.
# Test: uv run pytest tests/test_smoke_config.py

import os

from dotenv import load_dotenv

load_dotenv()

# Haiku 5.5 is the fast, cheap tier for classification; Sonnet 5.5 runs the agent.
MODEL_CLASSIFIER: str = "claude-haiku-5-5"
MODEL_AGENT: str = "claude-sonnet-5-5"

# Read here only. Never print, log, or put these in prompts or tool results.
ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
BANK_API_KEY: str | None = os.getenv("BANK_API_KEY")
BANK_ENV: str | None = os.getenv("BANK_ENV")
