# load_data.py: downloads BANKING77 (train and test) and saves both as CSV in data/.
# Why: every Phase 0 script reads this one local copy, so runs repeat exactly.
# It tries Hugging Face `datasets` first (not a project dependency, so it may fail),
# then falls back to the original CSVs in the PolyAI GitHub repo.
# Run: uv run python phase0_resolvability/load_data.py

import io
import re
from pathlib import Path

import httpx
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SPLITS = ("train", "test")
COLUMNS = ["text", "category"]
N_INTENTS = 77
GITHUB_BASE = (
    "https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets"
    "/master/banking_data"
)


def normalise_label(label: str) -> str:
    """Lowercase, trim, and drop punctuation such as '?'. Underscores stay."""
    return re.sub(r"[^\w\s]", "", label.strip().lower())


def load_from_hub() -> dict[str, pd.DataFrame]:
    # Imported here so a missing package is just a failed route, not a crash.
    from datasets import load_dataset

    dataset = load_dataset("PolyAI/banking77")
    names = dataset["train"].features["label"].names
    return {
        split: pd.DataFrame(
            {
                "text": dataset[split]["text"],
                "category": [names[i] for i in dataset[split]["label"]],
            }
        )
        for split in SPLITS
    }


def load_from_github() -> dict[str, pd.DataFrame]:
    frames = {}
    for split in SPLITS:
        response = httpx.get(
            f"{GITHUB_BASE}/{split}.csv", timeout=30, follow_redirects=True
        )
        response.raise_for_status()
        # keep_default_na=False: a query such as "NA" must stay text, not become NaN
        frames[split] = pd.read_csv(io.BytesIO(response.content), keep_default_na=False)
    return frames


def load_splits() -> tuple[str, dict[str, pd.DataFrame]]:
    try:
        return "Hugging Face datasets", load_from_hub()
    # ImportError: `datasets` not installed. RuntimeError: "Dataset scripts are no
    # longer supported". OSError: no network or dataset not found. Anything else is a bug.
    except (ImportError, RuntimeError, OSError) as exc:
        reason = (str(exc).splitlines() or [""])[0]
        print(f"Route 1 (datasets.load_dataset) failed: {type(exc).__name__}: {reason}")
        print("Falling back to route 2 (GitHub CSVs).")
    return "GitHub CSVs", load_from_github()


def normalise_categories(frames: dict[str, pd.DataFrame]) -> dict[str, str]:
    """Normalise the category column of every split in place.

    Returns {original: normalised} for the labels that changed.
    """
    changed: dict[str, str] = {}
    for df in frames.values():
        for original in df["category"].unique():
            normalised = normalise_label(original)
            if normalised != original:
                changed[original] = normalised
        df["category"] = df["category"].map(normalise_label)
    return changed


def check_columns(frames: dict[str, pd.DataFrame]) -> None:
    for split, df in frames.items():
        if list(df.columns) != COLUMNS:
            raise ValueError(
                f"{split}: expected columns {COLUMNS}, got {list(df.columns)}"
            )


def check_labels(frames: dict[str, pd.DataFrame]) -> None:
    label_sets = {split: set(df["category"]) for split, df in frames.items()}
    for split, labels in label_sets.items():
        if len(labels) != N_INTENTS:
            raise ValueError(f"{split}: expected {N_INTENTS} labels, got {len(labels)}")
    if label_sets["train"] != label_sets["test"]:
        raise ValueError("train and test do not have the same labels")


def main() -> None:
    route, frames = load_splits()
    print(f"Route used: {route}")
    for split, df in frames.items():
        print(f"  {split}: {len(df)} rows, columns {list(df.columns)}")
    check_columns(frames)

    changed = normalise_categories(frames)
    check_labels(frames)
    print(f"\nLabels changed by normalise_label: {len(changed)} of {N_INTENTS}")
    for original, normalised in sorted(changed.items()):
        print(f"  {original} -> {normalised}")

    DATA_DIR.mkdir(exist_ok=True)
    print()
    for split, df in frames.items():
        path = DATA_DIR / f"{split}.csv"
        df.to_csv(path, index=False)
        print(f"Saved {path.relative_to(DATA_DIR.parent)}")


if __name__ == "__main__":
    main()
