# sample.py: builds the DEV and TEST slices for Phase 0 from the saved BANKING77 CSVs.
# Why: DEV (from train) is for tuning prompts, TEST (from test) is for the final numbers,
# and the two must never share a query. Queries outside intents.yaml get gold label `other`.
# Run: uv run python -m phase0_resolvability.sample   (seed 42, so every run is identical)
# Test: uv run pytest tests/test_sample.py

import argparse
from pathlib import Path

import pandas as pd
import yaml

from phase0_resolvability.profile_data import read_splits

HERE = Path(__file__).resolve().parent
INTENTS_PATH = HERE / "intents.yaml"
SLICE_DIR = HERE.parent / "data" / "slices"  # under data/, so gitignored

SEED = 42
OTHER = "other"  # gold label for every query outside my in-scope intents
DEV_PER_INTENT = 20
DEV_OTHER = 100
TEST_OTHER = 200


def load_intent_names(path: Path = INTENTS_PATH) -> list[str]:
    entries = yaml.safe_load(path.read_text(encoding="utf-8"))["intents"]
    return [entry["name"] for entry in entries]


def draw(rows: pd.DataFrame, n: int, seed: int, what: str) -> pd.DataFrame:
    """Random n rows, or a clear error if there are not enough."""
    if len(rows) < n:
        raise ValueError(f"need {n} queries for {what}, only {len(rows)} available")
    return rows.sample(n=n, random_state=seed)


def label_slice(rows: pd.DataFrame, in_scope: list[str]) -> pd.DataFrame:
    """Keep text; gold_label is the intent if in scope, otherwise `other`."""
    gold = rows["category"].where(rows["category"].isin(in_scope), OTHER)
    return pd.DataFrame({"text": rows["text"], "gold_label": gold})


def shuffle(rows: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Mix the rows so the first N of a slice are not all one intent."""
    return rows.sample(frac=1, random_state=seed).reset_index(drop=True)


def check_no_overlap(dev: pd.DataFrame, test: pd.DataFrame) -> None:
    shared = set(dev["text"]) & set(test["text"])
    if shared:
        raise ValueError(f"{len(shared)} queries appear in both DEV and TEST")


def build_slices(
    train: pd.DataFrame,
    test: pd.DataFrame,
    in_scope: list[str],
    *,
    dev_per_intent: int = DEV_PER_INTENT,
    dev_other: int = DEV_OTHER,
    test_other: int = TEST_OTHER,
    seed: int = SEED,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (dev, test), each with columns text and gold_label, in shuffled order."""
    # TEST: every test query of the in-scope intents, plus random out-of-scope ones.
    test_in = test[test["category"].isin(in_scope)]
    for intent in in_scope:
        if not (test_in["category"] == intent).any():
            raise ValueError(f"{intent} has no queries in the test split")
    test_out = draw(
        test[~test["category"].isin(in_scope)], test_other, seed, "TEST out-of-scope"
    )
    test_rows = pd.concat([test_in, test_out])

    # DEV: from train, and never a text that appears anywhere in the test split.
    pool = train[~train["text"].isin(set(test["text"]))]
    dev_in = [
        draw(pool[pool["category"] == intent], dev_per_intent, seed, f"DEV {intent}")
        for intent in in_scope
    ]
    dev_out = draw(
        pool[~pool["category"].isin(in_scope)], dev_other, seed, "DEV out-of-scope"
    )
    dev_rows = pd.concat([*dev_in, dev_out])

    dev = shuffle(label_slice(dev_rows, in_scope), seed)
    test_slice = shuffle(label_slice(test_rows, in_scope), seed)
    check_no_overlap(dev, test_slice)
    return dev, test_slice


def print_counts(name: str, rows: pd.DataFrame) -> None:
    in_scope = rows[rows["gold_label"] != OTHER]
    print(
        f"{name}: {len(rows)} queries = {len(in_scope)} in scope "
        f"+ {len(rows) - len(in_scope)} {OTHER}"
    )
    for intent, count in in_scope["gold_label"].value_counts().sort_index().items():
        print(f"    {intent:<28} {count:>3}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the DEV and TEST slices.")
    parser.add_argument("--out-dir", type=Path, default=SLICE_DIR)
    args = parser.parse_args()

    frames = read_splits()
    dev, test = build_slices(frames["train"], frames["test"], load_intent_names())

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in (("dev", dev), ("test", test)):
        path = args.out_dir / f"{name}.csv"
        rows.to_csv(path, index=False)
        print_counts(f"{name.upper()} ({path})", rows)


if __name__ == "__main__":
    main()
