# make_report.py: fills the generated parts of report_template.md and writes report.md.
# Why: every number and score in the report comes from a saved run or intents.yaml, never from my hands;
# my own commentary lives in the template, and report.md is regenerated every time.
# Run: make report   (or: uv run python -m phase0_resolvability.make_report <before_run_id> <after_run_id>)
# Test: uv run pytest tests/test_make_report.py

import argparse
import re
import sys
from pathlib import Path

import yaml

from phase0_resolvability.compare import render_comparison_markdown
from phase0_resolvability.evaluate import (
    TIERS,
    Evaluation,
    evaluate_run,
    render_confusions,
    table,
)
from phase0_resolvability.sample import INTENTS_PATH

HERE = Path(__file__).resolve().parent
TEMPLATE_PATH = HERE / "report_template.md"
REPORT_PATH = HERE / "report.md"

SCORE_KEYS = ("data_api", "action", "policy_clarity", "risk", "ambiguity")
SCORES = (1, 2, 3)
LEGEND = (
    "Every score is 1, 2 or 3, and 3 is always better for a bot (risk 3 = low risk)."
)
BANNER = (
    "> **Generated file: do not edit by hand.** Written by `phase0_resolvability/make_report.py` "
    "from `phase0_resolvability/report_template.md` and the saved runs; change the template, "
    "then run `make report`."
)
# The two sentences are fixed wording, so they live here and a test checks them character by character.
LIMITS = (
    "BANKING77 is a curated, balanced dataset, so its intent mix is not real traffic and no volume figure here is a measurement.",
    "Gold labels are intents, not tiers; tier accuracy inherits each intent's tier from my scoring.",
)
LEADING_COMMENT = re.compile(
    r"\A<!--.*?-->\s*", re.DOTALL
)  # the template's header comment
PLACEHOLDER = re.compile(r"\{\{[A-Z_]+\}\}")


def load_intents(path: Path = INTENTS_PATH) -> list[dict]:
    """The entries of intents.yaml, checked for the fields the report prints."""
    entries = yaml.safe_load(path.read_text(encoding="utf-8"))["intents"]
    for entry in entries:
        name = entry.get("name")
        if set(entry.get("scores") or {}) != set(SCORE_KEYS):
            raise ValueError(
                f"{path.name}: {name}: scores must be exactly {SCORE_KEYS}"
            )
        bad = {
            key: value for key, value in entry["scores"].items() if value not in SCORES
        }
        if bad:
            raise ValueError(
                f"{path.name}: {name}: scores must be 1, 2 or 3; got {bad}"
            )
        if entry.get("tier") not in TIERS:
            raise ValueError(f"{path.name}: {name}: tier must be one of {TIERS}")
        if not entry.get("why"):
            raise ValueError(f"{path.name}: {name}: why is empty")
    return entries


def render_intents_table(intents: list[dict]) -> str:
    rows = [
        [
            f"`{entry['name']}`",
            *[str(entry["scores"][key]) for key in SCORE_KEYS],
            entry["tier"],
        ]
        for entry in intents
    ]
    return LEGEND + "\n\n" + table(["Intent", *SCORE_KEYS, "Tier"], rows)


def render_intent_whys(intents: list[dict]) -> str:
    """Each intent's `why` exactly as written in intents.yaml."""
    return "\n\n".join(f"### `{entry['name']}`\n\n{entry['why']}" for entry in intents)


def render_confusions_section(after: Evaluation) -> str:
    intro = (
        f"From the After run `{after.run_id}` ({after.slice_name.upper()} slice, "
        f"{after.total} queries): gold label against predicted label, most frequent first."
    )
    return intro + "\n\n" + render_confusions(after)


def render_limits() -> str:
    return "\n".join(f"- {sentence}" for sentence in LIMITS)


def fill_template(template: str, parts: dict[str, str]) -> str:
    """Replace each {{NAME}} with its generated part; the rest of the template is kept as written."""
    text = LEADING_COMMENT.sub("", template, count=1)
    for name, content in parts.items():
        marker = "{{" + name + "}}"
        if text.count(marker) != 1:
            raise ValueError(f"report template needs {marker} exactly once")
        text = text.replace(marker, content)
    leftover = PLACEHOLDER.findall(text)
    if leftover:
        raise ValueError(f"report template has unknown placeholders: {leftover}")
    return text


def render_report(
    template: str, before: Evaluation, after: Evaluation, intents: list[dict]
) -> str:
    parts = {
        "INTENTS_TABLE": render_intents_table(intents),
        "INTENT_WHYS": render_intent_whys(intents),
        "COMPARISON": render_comparison_markdown(before, after),
        "CONFUSIONS": render_confusions_section(after),
        "LIMITS": render_limits(),
    }
    return BANNER + "\n\n" + fill_template(template, parts).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Write report.md from two saved runs.")
    parser.add_argument("before", help="run id of the earlier run (prompt v1)")
    parser.add_argument("after", help="run id of the later run (prompt v3)")
    args = parser.parse_args()

    try:
        before = evaluate_run(args.before)
        after = evaluate_run(args.after)
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        report = render_report(template, before, after, load_intents())
    except (ValueError, OSError) as error:
        sys.exit(str(error))

    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT_PATH.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
