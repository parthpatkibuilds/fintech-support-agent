# evaluate.py: scores one classifier run (its predictions.csv) against the gold labels and intents.yaml.
# Why: turns raw predictions into the Phase 0 numbers; any figure quoted in a README or report
# must be copied from the summary.md and confusion.csv this writes, never typed by hand.
# Run: uv run python -m phase0_resolvability.evaluate <run_id>   (or --latest for the newest run)
# Test: uv run pytest tests/test_evaluate.py

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yaml

from phase0_resolvability.classify import INVALID, RESULTS_DIR, ROOT
from phase0_resolvability.sample import INTENTS_PATH, OTHER

TIERS = ("A", "B", "C")
NO_TIER = "none"  # the tier of `other`: not one of my in-scope intents
TOP_CONFUSIONS = 10
REQUIRED_COLUMNS = ["gold_label", "predicted", "prompt_version", "prompt_sha", "model"]
SLICES = ("dev", "test")
# classify.py names a run <timestamp>_<prompt>_<slice>[_n<limit>]. The limit is only recorded
# there; the slice is also a column, and the id is the fallback for runs made before that column.
RUN_ID_SLICE = re.compile(r"_(dev|test)(?:_n(\d+))?$")


@dataclass(frozen=True)
class Ratio:
    """hits out of total. Always printed with both counts, so no percentage stands alone."""

    hits: int
    total: int

    @property
    def percent(self) -> float | None:
        return 100 * self.hits / self.total if self.total else None

    def __str__(self) -> str:
        if self.percent is None:
            return f"n/a ({self.hits} of {self.total})"
        return f"{self.hits} of {self.total} ({self.percent:.1f}%)"


@dataclass(frozen=True)
class LabelScore:
    label: str
    precision: Ratio  # correct predictions of the label / all predictions of it
    recall: Ratio  # correct predictions of the label / all gold queries of it


@dataclass
class Evaluation:
    run_id: str
    slice_name: str  # "dev", "test" or "unknown"
    limit: int | None  # set when the run classified only the first N rows
    prompt_version: str
    prompt_sha: str
    model: str
    total: int
    invalid: Ratio
    intent_accuracy: Ratio
    other_share: Ratio
    tier_accuracy: Ratio
    confusions: list[
        tuple[str, str, int]
    ]  # (gold, predicted, count), most frequent first
    per_label: list[LabelScore]
    matrix: pd.DataFrame  # rows = gold labels, columns = predicted labels (+ invalid)

    @property
    def is_headline(self) -> bool:
        """Only a complete TEST run gives headline numbers."""
        return self.slice_name == "test" and self.limit is None

    def headline(self) -> list[tuple[str, Ratio]]:
        return [
            ("Intent accuracy, in-scope queries", self.intent_accuracy),
            ("Out-of-scope queries correctly labelled `other`", self.other_share),
            ("Tier accuracy, all queries", self.tier_accuracy),
        ]


def load_tiers(path: Path = INTENTS_PATH) -> dict[str, str]:
    """intent name -> tier, in the order intents.yaml lists them."""
    entries = yaml.safe_load(path.read_text(encoding="utf-8"))["intents"]
    tiers = {entry["name"]: entry["tier"] for entry in entries}
    bad = {name: tier for name, tier in tiers.items() if tier not in TIERS}
    if bad:
        raise ValueError(f"{path.name}: tier must be one of {TIERS}; got {bad}")
    return tiers


def tier_of(label: str, tiers: dict[str, str]) -> str:
    if label == OTHER:
        return NO_TIER
    if label == INVALID:
        return INVALID  # no usable answer: equals no gold tier, so it is always wrong
    return tiers[label]


def slice_of(run_id: str) -> tuple[str, int | None]:
    """(slice, limit) as written in the run id; ("unknown", None) if it has neither."""
    match = RUN_ID_SLICE.search(run_id)
    if match is None:
        return "unknown", None
    return match.group(1), int(match.group(2)) if match.group(2) else None


def slice_name_of(df: pd.DataFrame, run_id: str) -> str:
    """The slice the run classified: the recorded column if there is one, else the run id."""
    if "slice" not in df.columns:  # run made before classify.py recorded the slice
        return slice_of(run_id)[0]
    recorded = set(df["slice"])
    if len(recorded) != 1:
        raise ValueError(
            f"{run_id}: predictions mix several slices: {sorted(recorded)}"
        )
    (name,) = recorded
    return name if name in SLICES else "unknown"


def read_predictions(path: Path, valid_labels: list[str]) -> pd.DataFrame:
    df = pd.read_csv(path, keep_default_na=False)
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"{path}: missing columns {missing}")
    if df.empty:
        raise ValueError(f"{path}: no predictions")
    for column in ("gold_label", "predicted"):
        unknown = sorted(set(df[column]) - set(valid_labels))
        if unknown:
            raise ValueError(
                f"{path}: {column} has labels not in intents.yaml, `{OTHER}` or `{INVALID}`: {unknown}"
            )
    return df


def joined(df: pd.DataFrame, column: str) -> str:
    return ", ".join(sorted(df[column].astype(str).unique()))


def build_evaluation(
    run_id: str, df: pd.DataFrame, tiers: dict[str, str], top: int = TOP_CONFUSIONS
) -> Evaluation:
    labels = [*tiers, OTHER]
    gold, pred = df["gold_label"], df["predicted"]
    in_scope = gold != OTHER
    gold_tier = gold.map(lambda label: tier_of(label, tiers))
    pred_tier = pred.map(lambda label: tier_of(label, tiers))

    matrix = pd.crosstab(gold, pred).reindex(
        index=labels, columns=[*labels, INVALID], fill_value=0
    )
    matrix.index.name = "gold_label"
    matrix.columns.name = None

    wrong = df[gold != pred]
    counts = wrong.groupby(["gold_label", "predicted"]).size().reset_index(name="count")
    counts = counts.sort_values(
        ["count", "gold_label", "predicted"], ascending=[False, True, True]
    ).head(top)
    confusions = [(g, p, int(c)) for g, p, c in counts.itertuples(index=False)]

    per_label = []
    for label in labels:
        hits = int(((gold == label) & (pred == label)).sum())
        per_label.append(
            LabelScore(
                label,
                Ratio(hits, int((pred == label).sum())),
                Ratio(hits, int((gold == label).sum())),
            )
        )

    return Evaluation(
        run_id=run_id,
        slice_name=slice_name_of(df, run_id),
        limit=slice_of(run_id)[1],
        prompt_version=joined(df, "prompt_version"),
        prompt_sha=joined(df, "prompt_sha"),
        model=joined(df, "model"),
        total=len(df),
        invalid=Ratio(int((pred == INVALID).sum()), len(df)),
        intent_accuracy=Ratio(
            int((gold[in_scope] == pred[in_scope]).sum()), int(in_scope.sum())
        ),
        other_share=Ratio(
            int((pred[~in_scope] == OTHER).sum()), int((~in_scope).sum())
        ),
        tier_accuracy=Ratio(int((gold_tier == pred_tier).sum()), len(df)),
        confusions=confusions,
        per_label=per_label,
        matrix=matrix,
    )


def evaluate_run(
    run_id: str, results_dir: Path = RESULTS_DIR, intents_path: Path = INTENTS_PATH
) -> Evaluation:
    path = results_dir / run_id / "predictions.csv"
    if not path.is_file():
        raise ValueError(f"no predictions.csv for run {run_id!r} in {results_dir}")
    tiers = load_tiers(intents_path)
    df = read_predictions(path, [*tiers, OTHER, INVALID])
    return build_evaluation(run_id, df, tiers)


def latest_run_id(results_dir: Path = RESULTS_DIR) -> str:
    """The run whose predictions.csv was written last (works for custom --run-id names too)."""
    runs = list(results_dir.glob("*/predictions.csv"))
    if not runs:
        raise ValueError(f"no runs with a predictions.csv under {results_dir}")
    return max(runs, key=lambda p: (p.stat().st_mtime, p.parent.name)).parent.name


def banner(ev: Evaluation) -> str:
    partial = f" Partial run: only the first {ev.limit} queries." if ev.limit else ""
    if ev.slice_name == "unknown":
        return "**Slice unknown (the run id does not end in `_dev` or `_test`): not treated as headline numbers.**"
    if ev.slice_name == "dev":
        return f"**DEV slice: for prompt development. Do not quote these as headline numbers.**{partial}"
    if ev.limit:
        return f"**TEST slice, but a partial run (only the first {ev.limit} queries): not headline numbers.**"
    return "**TEST slice: these are the headline numbers.**"


def table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def render_confusions(ev: Evaluation) -> str:
    """The most frequent gold/predicted disagreements as a markdown table."""
    if not ev.confusions:
        return "None: every prediction matched its gold label."
    return table(
        ["Gold", "Predicted", "Count"],
        [[f"`{g}`", f"`{p}`", str(c)] for g, p, c in ev.confusions],
    )


def render_summary(ev: Evaluation) -> str:
    results = table(
        ["Metric", "Result"],
        [
            *[[name, str(ratio)] for name, ratio in ev.headline()],
            ["Invalid predictions (counted as wrong everywhere)", str(ev.invalid)],
        ],
    )
    confusions = render_confusions(ev)
    per_label = table(
        ["Label", "Precision", "Recall"],
        [[f"`{s.label}`", str(s.precision), str(s.recall)] for s in ev.per_label],
    )
    return f"""# Phase 0 evaluation: {ev.run_id}

{banner(ev)}

- Run: `{ev.run_id}` (prompt {ev.prompt_version}, sha256 `{ev.prompt_sha}`, model {ev.model})
- Source: `results/phase0/{ev.run_id}/predictions.csv`, {ev.total} queries
- Command: `uv run python -m phase0_resolvability.evaluate {ev.run_id}`

## Results

{results}

## {len(ev.confusions)} most frequent confusions

{confusions}

## Per-label precision and recall

{per_label}

## How to read this

- Intent accuracy: of the queries whose gold label is an in-scope intent, how many got exactly that intent.
- Tier accuracy: a query is correct when the tier of its gold label equals the tier of its predicted label.
  Tiers come from `intents.yaml`; `{OTHER}` has tier `{NO_TIER}`; an `{INVALID}` prediction has no tier and is always wrong.
  It counts every query, in-scope and `{OTHER}`, so a wrong intent inside the right tier still counts as correct.
- Precision of a label: correct predictions of it out of all predictions of it. Recall: correct predictions of it out of all gold queries of it. `n/a` means 0 of 0.
- Confusions are gold/predicted pairs that disagree; ties are listed alphabetically.
- `confusion.csv` is the full matrix: one row per gold label, one column per predicted label, plus an `{INVALID}` column.
"""


def write_outputs(ev: Evaluation, out_dir: Path) -> tuple[Path, Path]:
    summary = out_dir / "summary.md"
    confusion = out_dir / "confusion.csv"
    summary.write_text(render_summary(ev), encoding="utf-8")
    ev.matrix.to_csv(confusion)
    return summary, confusion


def main() -> None:
    parser = argparse.ArgumentParser(description="Score a classifier run.")
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument("run_id", nargs="?", help="folder name under results/phase0/")
    which.add_argument(
        "--latest",
        action="store_true",
        help="the run whose predictions.csv was written last",
    )
    args = parser.parse_args()

    try:
        run_id = latest_run_id() if args.latest else args.run_id
        evaluation = evaluate_run(run_id)
    except ValueError as error:
        sys.exit(str(error))

    summary, confusion = write_outputs(evaluation, RESULTS_DIR / run_id)
    print(
        f"Run {run_id}: {evaluation.slice_name.upper()} slice, {evaluation.total} queries"
    )
    print(f"Wrote {summary.relative_to(ROOT)}")
    print(f"Wrote {confusion.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
