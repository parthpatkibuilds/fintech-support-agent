# Smoke test: config.py imports, and no API key value is hard-coded in the repo.
# Why: CLAUDE.md rule 2 keeps secrets in .env only; this catches a pasted key.
# It reports file and line only, never the matched text, so it cannot leak a key.
# Run: uv run pytest tests/test_smoke_config.py

import os
import re
from pathlib import Path

import config

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "data"}
SKIP_FILES = {".env", "uv.lock"}  # .env is where real values belong; it is gitignored

KEY_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_-]{10,}"),
    # NAME = "literal" in code
    re.compile(r"(?:ANTHROPIC_API_KEY|BANK_API_KEY)\s*(?::[^=\n]+)?=\s*[\"'][^\"']+[\"']"),
    # NAME=value at the start of a line, as in an env file
    re.compile(r"^(?:ANTHROPIC_API_KEY|BANK_API_KEY)=\S+", re.MULTILINE),
]


def repo_text_files():
    for folder, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]  # prune: never enter .venv
        for name in files:
            if name in SKIP_FILES:
                continue
            path = Path(folder) / name
            try:
                yield path, path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue  # binary or unreadable: nothing to scan


def test_config_imports_and_no_api_key_is_hardcoded():
    assert config.MODEL_CLASSIFIER.startswith("claude-")
    assert config.MODEL_AGENT.startswith("claude-")

    real_values = [v for v in (config.ANTHROPIC_API_KEY, config.BANK_API_KEY) if v]
    problems = []
    for path, text in repo_text_files():
        rel = path.relative_to(ROOT)
        for pattern in KEY_PATTERNS:
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                problems.append(f"{rel}:{line} looks like a hard-coded key")
        if any(value in text for value in real_values):
            problems.append(f"{rel} contains the real value loaded from .env")

    assert not problems, "\n".join(problems)
