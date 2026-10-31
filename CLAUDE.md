# CLAUDE.md

## What this repo is
A portfolio project for a Forward Deployed Engineering internship application, built by a student who is learning as he builds and must be able to explain every file in an interview. It has three parts: (1) a ticket-resolvability analysis on the public BANKING77 dataset, (2) a support agent for a FICTIONAL neobank that handles lost or stolen debit card tickets through a mock bank API, (3) an eval harness and red-team results.

## Hard rules
1. All writes go through workflows. In the final design the model never calls a write endpoint directly. Writes happen only inside deterministic workflows (agent/workflows/) that check preconditions against recorded bank state, never against what the model or the customer claims. The only exception is the baseline mode in agent/tools_raw.py, labelled BASELINE - UNSAFE BY DESIGN, used for evals against the synthetic bank.
2. Secrets never enter model context. API keys live in .env, are read in code only, and never appear in prompts, tool arguments, tool results, logs, tests or fixtures. Tool results sent to the model are minimal and masked.
3. Every deterministic workflow has tests. A workflow is not done until a table-driven pytest covers every transition and at least one illegal transition. Tests never call the real Anthropic API; use a stub client.
4. Synthetic data only. No real names, emails, phone numbers, addresses or card numbers, ever. Use example.com emails, fictional names, and last-4 plus a token for cards. BANKING77 is the only external data.
5. No invented numbers. Every figure in a README or report comes from a file under results/ produced by a command. Never type a metric by hand.

## Working rules
- Do only the step I ask for. No extra features and no new dependencies without asking first.
- Stack: Python 3.12+, uv, pytest, ruff, type hints; FastAPI and SQLite for the mock bank; the Anthropic Python SDK for the model.
- Model IDs live only in config.py. Check the current Claude API docs before using a model or API feature; do not guess.
- Keep files small, one job each. Start every new file with a 3 to 5 line comment: what it does, why it exists, how to test it.
- After each step, stop and tell me: the files changed, a short explanation of each file, and the command to run it. Wait for me before the next step.
- Commit after each working step with a plain message.
- BANKING77 is CC BY 4.0 (PolyAI; Casanueva et al., 2020). Credit it in the README and keep raw data out of git except small samples.
