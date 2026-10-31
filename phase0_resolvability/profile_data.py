# profile_data.py: prints a profile of the saved BANKING77 splits.
# Why: look at the real data (sizes, balance, example queries) before judging
# which intents a bot could resolve. Needs data/ from load_data.py first.
# Run: uv run python phase0_resolvability/profile_data.py lost_or_stolen_card card_arrival

import argparse
import difflib
import sys
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SPLITS = ("train", "test")
SAMPLES_PER_INTENT = 5
SEED = 0  # fixed, so the "random" samples are the same on every run


def read_splits() -> dict[str, pd.DataFrame]:
    frames = {}
    for split in SPLITS:
        path = DATA_DIR / f"{split}.csv"
        if not path.exists():
            sys.exit(
                f"{path} is missing. Run: uv run python phase0_resolvability/load_data.py"
            )
        frames[split] = pd.read_csv(path, keep_default_na=False)
    return frames


def count_table(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """One row per intent (A to Z), one column per split."""
    counts = pd.DataFrame(
        {s: df["category"].value_counts() for s, df in frames.items()}
    )
    return counts.fillna(0).astype(int).sort_index()


def describe_balance(column: pd.Series) -> str:
    low, high = column.min(), column.max()
    if low == high:
        return f"all {len(column)} intents have exactly {low} queries (balanced)"
    return (
        f"min {low} ({column.idxmin()}), median {column.median():g}, "
        f"max {high} ({column.idxmax()})"
    )


def print_overview(frames: dict[str, pd.DataFrame], counts: pd.DataFrame) -> None:
    print("== Rows per split")
    for split, df in frames.items():
        print(f"  {split:<5} {len(df):>6}")

    print(f"\n== The {len(counts)} intents: queries per intent in each split")
    width = max(len(label) for label in counts.index)
    header = "  ".join(f"{split:>5}" for split in counts.columns)
    print(f"  {'#':>2}  {'intent':<{width}}  {header}")
    for number, (label, row) in enumerate(counts.iterrows(), start=1):
        numbers = "  ".join(f"{n:>5}" for n in row)
        print(f"  {number:>2}  {label:<{width}}  {numbers}")

    print("\n== Balance (queries per intent)")
    for split in counts.columns:
        print(f"  {split:<5} {describe_balance(counts[split])}")


def print_samples(
    frames: dict[str, pd.DataFrame], counts: pd.DataFrame, intents: list[str]
) -> None:
    print(
        f"\n== {SAMPLES_PER_INTENT} random train queries per requested intent (seed {SEED})"
    )
    train = frames["train"]
    for intent in intents:
        queries = train.loc[train["category"] == intent, "text"]
        picked = queries.sample(
            n=min(SAMPLES_PER_INTENT, len(queries)), random_state=SEED
        )
        sizes = (
            f"{counts.loc[intent, 'train']} train, {counts.loc[intent, 'test']} test"
        )
        print(f"\n{intent} ({sizes})")
        for query in picked:
            print(f"  - {query}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile the saved BANKING77 data.")
    parser.add_argument(
        "intents", nargs="*", help="intent names to sample, e.g. lost_or_stolen_card"
    )
    args = parser.parse_args()

    frames = read_splits()
    counts = count_table(frames)
    for intent in args.intents:
        if intent not in counts.index:
            close = difflib.get_close_matches(intent, list(counts.index), n=3)
            parser.error(
                f"unknown intent {intent!r}; closest: {', '.join(close) or 'none'}"
            )

    print_overview(frames, counts)
    print_samples(frames, counts, args.intents)


if __name__ == "__main__":
    main()
