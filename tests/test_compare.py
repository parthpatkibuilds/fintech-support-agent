# Tests for phase0_resolvability/compare.py: the change column, the warnings, the printed table.
# Why: a before-and-after table is how I decide whether a prompt change helped, so it must not mislead.
# Builds Evaluation objects from tiny made-up frames; no API and no data/ needed.
# Run: uv run pytest tests/test_compare.py

import pandas as pd
import pytest

from phase0_resolvability.classify import INVALID
from phase0_resolvability.compare import (
    change,
    render_comparison,
    render_comparison_markdown,
    warnings,
)
from phase0_resolvability.evaluate import Ratio, build_evaluation
from phase0_resolvability.sample import OTHER

TIERS = {"a": "A", "b": "B"}


def evaluation(run_id: str, pairs: list[tuple[str, str]], version: str = "v1"):
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


BEFORE_PAIRS = [("a", "b"), ("a", "a"), ("b", "b"), (OTHER, "a")]  # 2/3, 0/1, tier 2/4
AFTER_PAIRS = [("a", "a"), ("a", "a"), ("b", "b"), (OTHER, OTHER)]  # 3/3, 1/1, tier 4/4


@pytest.mark.parametrize(
    ("before", "after", "expected"),
    [
        (Ratio(1, 2), Ratio(3, 4), "+25.0 pp"),
        (Ratio(3, 4), Ratio(1, 2), "-25.0 pp"),
        (Ratio(1, 2), Ratio(2, 4), "+0.0 pp"),
        (Ratio(0, 0), Ratio(1, 2), "n/a"),
        (Ratio(1, 2), Ratio(0, 0), "n/a"),
    ],
)
def test_change_is_in_percentage_points(before, after, expected):
    assert change(before, after) == expected


def test_table_shows_both_runs_with_counts_and_the_change():
    before = evaluation("20261101T000000Z_v1_dev", BEFORE_PAIRS, "v1")
    after = evaluation("20261101T000000Z_v2_dev", AFTER_PAIRS, "v2")

    lines = render_comparison(before, after).splitlines()

    assert "Before: 20261101T000000Z_v1_dev  (prompt v1, DEV slice, 4 queries)" in lines
    assert "After : 20261101T000000Z_v2_dev  (prompt v2, DEV slice, 4 queries)" in lines
    row = next(line for line in lines if line.startswith("Intent accuracy"))
    assert "2 of 3 (66.7%)" in row and "3 of 3 (100.0%)" in row and "+33.3 pp" in row
    other = next(line for line in lines if line.startswith("Out-of-scope"))
    assert (
        "0 of 1 (0.0%)" in other and "1 of 1 (100.0%)" in other and "+100.0 pp" in other
    )
    tier = next(line for line in lines if line.startswith("Tier accuracy"))
    assert "2 of 4 (50.0%)" in tier and "4 of 4 (100.0%)" in tier and "+50.0 pp" in tier
    assert not any(line.startswith("WARNING") for line in lines)


def test_table_has_only_the_three_headline_rows():
    ev = evaluation("20261101T000000Z_v1_dev", BEFORE_PAIRS)

    lines = render_comparison(ev, ev).splitlines()

    assert len(lines) == 2 + 1 + 1 + 3  # two run lines, blank, header, three metrics
    assert INVALID not in "\n".join(lines)


@pytest.mark.parametrize(
    ("before_id", "after_id", "expected"),
    [
        ("x_v1_dev", "x_v2_dev", []),
        ("x_v1_test", "x_v2_test", []),
        ("x_v1_dev", "x_v2_test", ["different slices (DEV vs TEST)"]),
        ("x_v1_dev_n20", "x_v2_dev", ["x_v1_dev_n20 is a partial run (first 20"]),
        ("x_v1_dev", "x_v2_dev_n5", ["x_v2_dev_n5 is a partial run (first 5"]),
    ],
)
def test_warnings(before_id, after_id, expected):
    found = warnings(
        evaluation(before_id, BEFORE_PAIRS), evaluation(after_id, AFTER_PAIRS)
    )

    assert len(found) == len(expected)
    assert all(want in got for want, got in zip(expected, found))


def test_markdown_table_keeps_the_counts_next_to_the_percentages():
    before = evaluation("x_v1_test", BEFORE_PAIRS, "v1")
    after = evaluation("x_v2_test", AFTER_PAIRS, "v2")

    lines = render_comparison_markdown(before, after).splitlines()

    assert "- Before: `x_v1_test` (prompt v1, TEST slice, 4 queries)" in lines
    assert "- After: `x_v2_test` (prompt v2, TEST slice, 4 queries)" in lines
    assert "| Metric | Before | After | Change |" in lines
    assert (
        "| Intent accuracy, in-scope queries | 2 of 3 (66.7%) | 3 of 3 (100.0%) | +33.3 pp |"
        in lines
    )
    assert not any("WARNING" in line for line in lines)


def test_markdown_warnings_come_after_the_table():
    text = render_comparison_markdown(
        evaluation("x_v1_dev", BEFORE_PAIRS), evaluation("x_v2_test", AFTER_PAIRS)
    )

    assert text.splitlines()[-1].startswith("> WARNING: the runs use different slices")


def test_warnings_are_printed_at_the_end():
    text = render_comparison(
        evaluation("x_v1_dev", BEFORE_PAIRS), evaluation("x_v2_test", AFTER_PAIRS)
    )

    assert text.splitlines()[-1].startswith("WARNING: the runs use different slices")
