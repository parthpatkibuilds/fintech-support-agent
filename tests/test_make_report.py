# Tests for phase0_resolvability/make_report.py: template filling, the intents table, the Limits wording.
# Why: report.md is regenerated from the template every time, so a lost placeholder, a changed
# Limits sentence or a `why` that is not verbatim must fail here and not in front of a reader.
# Uses made-up Evaluations and the real intents.yaml and report_template.md; no API and no data/ needed.
# Run: uv run pytest tests/test_make_report.py

import pandas as pd
import pytest
import yaml

from phase0_resolvability.evaluate import Evaluation, build_evaluation
from phase0_resolvability.make_report import (
    BANNER,
    LEGEND,
    TEMPLATE_PATH,
    fill_template,
    load_intents,
    render_confusions_section,
    render_intent_whys,
    render_intents_table,
    render_limits,
    render_report,
)
from phase0_resolvability.sample import INTENTS_PATH, OTHER

TIERS = {"a": "A", "b": "B"}
INTENTS = [
    {
        "name": "a",
        "scores": {
            "data_api": 3,
            "action": 2,
            "policy_clarity": 1,
            "risk": 3,
            "ambiguity": 2,
        },
        "tier": "A",
        "why": "Why a, with a trailing space. ",
    },
    {
        "name": "b",
        "scores": {
            "data_api": 1,
            "action": 1,
            "policy_clarity": 2,
            "risk": 1,
            "ambiguity": 3,
        },
        "tier": "B",
        "why": "Why b & more_underscores.",
    },
]
TEMPLATE = """<!-- header comment: dropped
     {{NOT_A_REAL_PLACEHOLDER}} -->

# Title

## Findings

<!-- YOU WRITE THIS -->

{{INTENTS_TABLE}}

{{INTENT_WHYS}}

{{COMPARISON}}

{{CONFUSIONS}}

## Limits

{{LIMITS}}
"""


def evaluation(
    run_id: str, pairs: list[tuple[str, str]], version: str = "v1"
) -> Evaluation:
    df = pd.DataFrame(
        {
            "gold_label": [gold for gold, _ in pairs],
            "predicted": [pred for _, pred in pairs],
            "prompt_version": version,
            "prompt_sha": "e" * 64,
            "model": "stub-model",
        }
    )
    return build_evaluation(run_id, df, TIERS)


BEFORE = evaluation(
    "x_v1_test", [("a", "b"), ("a", "a"), ("b", "b"), (OTHER, "a")], "v1"
)  # intent 2/3, other 0/1, tier 2/4
AFTER = evaluation(
    "x_v3_test", [("a", "a"), ("a", "a"), ("b", OTHER), (OTHER, "b")], "v3"
)  # intent 2/3, other 0/1, tier 2/4; confusions: b->other and other->b


def report() -> str:
    return render_report(TEMPLATE, BEFORE, AFTER, INTENTS)


def test_intents_table_has_name_five_scores_tier_and_the_legend():
    text = render_intents_table(INTENTS)

    lines = text.splitlines()
    assert lines[0] == LEGEND
    assert "3 is always better for a bot (risk 3 = low risk)" in LEGEND
    assert (
        lines[2]
        == "| Intent | data_api | action | policy_clarity | risk | ambiguity | Tier |"
    )
    assert "| `a` | 3 | 2 | 1 | 3 | 2 | A |" in lines
    assert "| `b` | 1 | 1 | 2 | 1 | 3 | B |" in lines


def test_every_why_is_copied_verbatim_under_its_intent():
    text = render_intent_whys(INTENTS)

    assert (
        text
        == "### `a`\n\nWhy a, with a trailing space. \n\n### `b`\n\nWhy b & more_underscores."
    )


def test_real_intents_file_is_reported_in_full_and_verbatim():
    raw = yaml.safe_load(INTENTS_PATH.read_text(encoding="utf-8"))["intents"]
    intents = load_intents()

    table_text = render_intents_table(intents)
    whys_text = render_intent_whys(intents)

    assert len(intents) == len(raw)
    for entry in raw:
        assert f"| `{entry['name']}` |" in table_text
        assert f"### `{entry['name']}`\n\n{entry['why']}" in whys_text


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda e: e["scores"].pop("risk"), "scores must be exactly"),
        (lambda e: e["scores"].update(risk=None), "scores must be 1, 2 or 3"),
        (lambda e: e["scores"].update(risk=4), "scores must be 1, 2 or 3"),
        (lambda e: e.update(tier="D"), "tier must be one of"),
        (lambda e: e.update(tier=None), "tier must be one of"),
        (lambda e: e.update(why=""), "why is empty"),
    ],
)
def test_load_intents_rejects_unfinished_entries(tmp_path, change, message):
    entry = {**INTENTS[0], "scores": dict(INTENTS[0]["scores"])}
    change(entry)
    path = tmp_path / "intents.yaml"
    path.write_text(yaml.safe_dump({"intents": [entry]}), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_intents(path)


def test_limits_contain_the_two_required_sentences_exactly():
    assert render_limits().splitlines() == [
        "- BANKING77 is a curated, balanced dataset, so its intent mix is not real traffic and no volume figure here is a measurement.",
        "- Gold labels are intents, not tiers; tier accuracy inherits each intent's tier from my scoring.",
    ]


def test_confusions_are_those_of_the_after_run_only():
    text = render_confusions_section(AFTER)

    assert "x_v3_test" in text and "x_v1_test" not in text
    assert "| `b` | `other` | 1 |" in text and "| `other` | `b` | 1 |" in text
    assert "| `a` | `b` |" not in text  # the Before run's mistake


def test_report_starts_with_the_generated_file_line_and_drops_the_template_header():
    text = report()

    assert text.startswith(BANNER + "\n\n# Title")
    assert "do not edit by hand" in text.splitlines()[0]
    assert "header comment" not in text
    assert "NOT_A_REAL_PLACEHOLDER" not in text


def test_report_fills_every_generated_part_and_keeps_my_placeholders_empty():
    text = report()

    assert "{{" not in text
    assert (
        text.count("<!-- YOU WRITE THIS -->") == 1
    )  # untouched, nothing written under it
    assert LEGEND in text
    assert "### `b`" in text
    assert "- Before: `x_v1_test` (prompt v1, TEST slice, 4 queries)" in text
    assert "- After: `x_v3_test` (prompt v3, TEST slice, 4 queries)" in text
    assert text.endswith("from my scoring.\n")


@pytest.mark.parametrize(
    ("template", "message"),
    [
        (TEMPLATE.replace("{{LIMITS}}", ""), r"needs \{\{LIMITS\}\} exactly once"),
        (TEMPLATE + "{{LIMITS}}", r"needs \{\{LIMITS\}\} exactly once"),
        (TEMPLATE + "{{TYPO}}", "unknown placeholders"),
    ],
)
def test_template_with_a_lost_repeated_or_unknown_placeholder_is_rejected(
    template, message
):
    with pytest.raises(ValueError, match=message):
        render_report(template, BEFORE, AFTER, INTENTS)


def test_fill_template_leaves_text_with_braces_alone():
    text = fill_template("code: {x} and {{A}}", {"A": "done"})

    assert text == "code: {x} and done"


def test_the_real_template_fills_cleanly_with_every_section():
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    text = render_report(template, BEFORE, AFTER, load_intents())

    assert "{{" not in text
    assert "report_template.md:" not in text  # the header comment stays in the template
    for heading in (
        "## Findings",
        "## Why the confusions happen",
        "## What AI cannot resolve yet",
        "## Limits",
    ):
        assert heading in text
    assert "BANKING77 is a curated, balanced dataset" in text
