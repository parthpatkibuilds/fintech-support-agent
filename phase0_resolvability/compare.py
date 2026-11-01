# compare.py: prints a before-and-after table of the headline numbers for two runs.
# Why: shows whether a new prompt version moved the numbers, scored by the same code as evaluate.py.
# render_comparison_markdown gives the same table as markdown for make_report.py.
# Run: uv run python -m phase0_resolvability.compare <before_run_id> <after_run_id>
# Test: uv run pytest tests/test_compare.py

import argparse
import sys

from phase0_resolvability.evaluate import Evaluation, Ratio, evaluate_run, table


def change(before: Ratio, after: Ratio) -> str:
    """After minus before, in percentage points."""
    if before.percent is None or after.percent is None:
        return "n/a"
    return f"{after.percent - before.percent:+.1f} pp"


def warnings(before: Evaluation, after: Evaluation) -> list[str]:
    found = []
    if before.slice_name != after.slice_name:
        found.append(
            f"the runs use different slices ({before.slice_name.upper()} vs {after.slice_name.upper()}); "
            "the numbers are not comparable."
        )
    for ev in (before, after):
        if ev.limit is not None:
            found.append(f"{ev.run_id} is a partial run (first {ev.limit} queries).")
    return found


def describe(role: str, ev: Evaluation) -> str:
    return f"{role}: {ev.run_id}  (prompt {ev.prompt_version}, {ev.slice_name.upper()} slice, {ev.total} queries)"


def render_comparison(before: Evaluation, after: Evaluation) -> str:
    rows = [["Metric", "Before", "After", "Change"]]
    for (name, old), (_, new) in zip(before.headline(), after.headline()):
        rows.append([name, str(old), str(new), change(old, new)])
    widths = [max(len(row[i]) for row in rows) for i in range(4)]
    lines = [describe("Before", before), describe("After ", after), ""]
    lines += [
        "  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip()
        for row in rows
    ]
    for warning in warnings(before, after):
        lines += ["", f"WARNING: {warning}"]
    return "\n".join(lines)


def render_comparison_markdown(before: Evaluation, after: Evaluation) -> str:
    """The same numbers as render_comparison, as markdown for the report."""
    runs = [
        f"- {role}: `{ev.run_id}` (prompt {ev.prompt_version}, {ev.slice_name.upper()} slice, {ev.total} queries)"
        for role, ev in (("Before", before), ("After", after))
    ]
    rows = [
        [name, str(old), str(new), change(old, new)]
        for (name, old), (_, new) in zip(before.headline(), after.headline())
    ]
    parts = [
        "\n".join(runs),
        table(["Metric", "Before", "After", "Change"], rows),
        *[f"> WARNING: {warning}" for warning in warnings(before, after)],
    ]
    return "\n\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two classifier runs.")
    parser.add_argument("before", help="run id of the earlier run")
    parser.add_argument("after", help="run id of the later run")
    args = parser.parse_args()

    try:
        before = evaluate_run(args.before)
        after = evaluate_run(args.after)
    except ValueError as error:
        sys.exit(str(error))
    print(render_comparison(before, after))


if __name__ == "__main__":
    main()
