# Tests for phase0_resolvability/sample.py: slice sizes, `other` labels, and no DEV/TEST overlap.
# Why: a query in both slices would let prompt tuning leak into the final numbers.
# Uses tiny made-up frames, not BANKING77, so it runs without data/.
# Run: uv run pytest tests/test_sample.py

import pandas as pd
import pytest

from phase0_resolvability.sample import OTHER, build_slices, check_no_overlap

IN_SCOPE = ["alpha_one", "beta_two"]
SIZES = {"dev_per_intent": 3, "dev_other": 4, "test_other": 5}


def frame(split: str, per_intent: int, extra: list[tuple[str, str]]) -> pd.DataFrame:
    rows = [
        (f"{split} {intent} {i}", intent)
        for intent in ["alpha_one", "beta_two", "gamma_three", "delta_four"]
        for i in range(per_intent)
    ]
    return pd.DataFrame([*rows, *extra], columns=["text", "category"])


@pytest.fixture
def splits():
    # "shared a" is in both splits as an in-scope query; "shared b" as an out-of-scope one.
    shared = [("shared a", "alpha_one"), ("shared b", "gamma_three")]
    return frame("train", 8, shared), frame("test", 8, shared)


def test_slice_sizes_and_labels(splits):
    dev, test = build_slices(*splits, IN_SCOPE, **SIZES)

    assert list(dev.columns) == ["text", "gold_label"]
    assert len(dev) == 3 * len(IN_SCOPE) + 4
    assert dev["gold_label"].value_counts().to_dict() == {
        "alpha_one": 3,
        "beta_two": 3,
        OTHER: 4,
    }
    # TEST: every in-scope test query (9 alpha_one incl. shared a, 8 beta_two) + 5 other.
    assert test["gold_label"].value_counts().to_dict() == {
        "alpha_one": 9,
        "beta_two": 8,
        OTHER: 5,
    }
    assert set(dev["gold_label"]) <= {*IN_SCOPE, OTHER}


def test_dev_and_test_share_no_query(splits):
    dev, test = build_slices(*splits, IN_SCOPE, **SIZES)

    assert not set(dev["text"]) & set(test["text"])
    # Texts that sit in both source splits are kept out of DEV, even "shared b",
    # which the random out-of-scope draw may not have put into TEST.
    assert not {"shared a", "shared b"} & set(dev["text"])


def test_check_no_overlap_rejects_a_shared_text():
    dev = pd.DataFrame({"text": ["x", "y"], "gold_label": [OTHER, OTHER]})
    test = pd.DataFrame({"text": ["y", "z"], "gold_label": [OTHER, OTHER]})
    with pytest.raises(ValueError, match="1 queries appear in both"):
        check_no_overlap(dev, test)


def test_same_seed_gives_same_slices(splits):
    first = build_slices(*splits, IN_SCOPE, **SIZES)
    second = build_slices(*splits, IN_SCOPE, **SIZES)
    for a, b in zip(first, second):
        pd.testing.assert_frame_equal(a, b)


@pytest.mark.parametrize(
    "sizes, message",
    [
        ({"dev_per_intent": 99, "dev_other": 4, "test_other": 5}, "DEV alpha_one"),
        ({"dev_per_intent": 3, "dev_other": 99, "test_other": 5}, "DEV out-of-scope"),
        ({"dev_per_intent": 3, "dev_other": 4, "test_other": 99}, "TEST out-of-scope"),
    ],
)
def test_too_few_queries_is_an_error(splits, sizes, message):
    with pytest.raises(ValueError, match=message):
        build_slices(*splits, IN_SCOPE, **sizes)


def test_intent_missing_from_test_split_is_an_error(splits):
    train, test = splits
    test = test[test["category"] != "beta_two"]
    with pytest.raises(ValueError, match="beta_two has no queries in the test split"):
        build_slices(train, test, IN_SCOPE, **SIZES)
