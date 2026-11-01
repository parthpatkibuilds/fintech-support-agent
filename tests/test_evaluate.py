# Tests for phase0_resolvability/evaluate.py: every metric, the tier mapping, run lookup, output files.
# Why: these numbers go into the README, so the arithmetic must be checked by hand on a tiny frame.
# Uses made-up labels and a made-up tier table; no API and no data/ needed.
# Run: uv run pytest tests/test_evaluate.py

import os

import pandas as pd
import pytest

from phase0_resolvability.classify import INVALID
from phase0_resolvability.evaluate import (
    NO_TIER,
    Ratio,
    build_evaluation,
    evaluate_run,
    latest_run_id,
    load_tiers,
    read_predictions,
    render_summary,
    slice_of,
    tier_of,
    write_outputs,
)
from phase0_resolvability.sample import OTHER

TIERS = {"a": "A", "b": "B", "c": "B", "d": "C"}
LABELS = [*TIERS, OTHER, INVALID]

# (gold, predicted), worked out by hand in the comments of the tests below.
PAIRS = [
    ("a", "a"),
    ("a", "a"),
    ("a", "b"),  # wrong intent, and A vs B: wrong tier
    ("a", "b"),
    ("b", "c"),  # wrong intent, but B vs B: right tier
    ("b", "b"),
    ("c", OTHER),  # in-scope query sent to other: B vs none, wrong tier
    ("d", INVALID),  # no usable answer
    ("d", "d"),
    (OTHER, OTHER),
    (OTHER, OTHER),
    (OTHER, OTHER),
    (OTHER, "a"),  # out-of-scope query given an intent: none vs A, wrong tier
]


def frame(pairs: list[tuple[str, str]], slice_name: str | None = None) -> pd.DataFrame:
    """slice_name=None builds a file from before classify.py recorded the slice."""
    df = pd.DataFrame(
        {
            "text": [f"query {i}" for i in range(len(pairs))],
            "gold_label": [gold for gold, _ in pairs],
            "predicted": [pred for _, pred in pairs],
            "prompt_version": "v9",
            "prompt_sha": "f" * 64,
            "model": "stub-model",
        }
    )
    if slice_name is not None:
        df["slice"] = slice_name
    return df


@pytest.mark.parametrize(
    ("hits", "total", "expected"),
    [
        (112, 120, "112 of 120 (93.3%)"),
        (0, 5, "0 of 5 (0.0%)"),
        (5, 5, "5 of 5 (100.0%)"),
        (0, 0, "n/a (0 of 0)"),
    ],
)
def test_ratio_always_shows_the_counts(hits, total, expected):
    assert str(Ratio(hits, total)) == expected


@pytest.mark.parametrize(
    ("label", "expected"),
    [("a", "A"), ("b", "B"), ("d", "C"), (OTHER, NO_TIER), (INVALID, INVALID)],
)
def test_tier_of(label, expected):
    assert tier_of(label, TIERS) == expected


@pytest.mark.parametrize(
    ("run_id", "expected"),
    [
        ("20261101T100039Z_v2_dev", ("dev", None)),
        ("20261101T103105Z_v3_test", ("test", None)),
        ("20261101T081730Z_v1_dev_n20", ("dev", 20)),
        ("20261101T081730Z_v1_test_n5", ("test", 5)),
        ("my_custom_run", ("unknown", None)),
        ("development_run", ("unknown", None)),
    ],
)
def test_slice_of(run_id, expected):
    assert slice_of(run_id) == expected


@pytest.mark.parametrize(
    ("recorded", "run_id", "slice_name", "limit"),
    [
        ("test", "custom_run", "test", None),  # the column alone is enough
        ("dev", "custom_run", "dev", None),
        ("test", "x_v1_dev", "test", None),  # the column wins over a misleading id
        ("holdout", "x_v1_test", "unknown", None),  # recorded, but neither dev nor test
        ("dev", "x_v1_dev_n20", "dev", 20),  # the limit is only in the id
        ("test", "x_v1_test_n20", "test", 20),
        (
            None,
            "x_v1_test",
            "test",
            None,
        ),  # older run, no column: the id is the fallback
        (None, "x_v1_dev_n20", "dev", 20),
        (None, "custom_run", "unknown", None),
    ],
)
def test_slice_comes_from_the_column_with_the_run_id_as_fallback(
    recorded, run_id, slice_name, limit
):
    ev = build_evaluation(run_id, frame(PAIRS, recorded), TIERS)

    assert (ev.slice_name, ev.limit) == (slice_name, limit)
    assert ev.is_headline == (slice_name == "test" and limit is None)


def test_a_file_that_mixes_slices_is_rejected():
    df = frame(PAIRS[:2])
    df["slice"] = ["dev", "test"]

    with pytest.raises(ValueError, match="mix several slices"):
        build_evaluation("x_v1_test", df, TIERS)


def test_headline_numbers():
    ev = build_evaluation("r_test", frame(PAIRS), TIERS)

    # 9 in-scope rows (a x4, b x2, c, d x2); right: a,a,b,d = 4.
    assert ev.intent_accuracy == Ratio(4, 9)
    # 4 out-of-scope rows; 3 labelled other.
    assert ev.other_share == Ratio(3, 4)
    # Right tier: a,a (A=A), b->c (B=B), b, other x3 (none=none), d (C=C) = 8 of 13.
    assert ev.tier_accuracy == Ratio(8, 13)
    assert ev.invalid == Ratio(1, 13)
    assert ev.total == 13


def test_invalid_is_wrong_for_in_scope_and_out_of_scope_alike():
    ev = build_evaluation("r_test", frame([("a", INVALID), (OTHER, INVALID)]), TIERS)

    assert ev.intent_accuracy == Ratio(0, 1)
    assert ev.other_share == Ratio(0, 1)
    assert ev.tier_accuracy == Ratio(0, 2)  # invalid must not count as tier `none`


def test_confusions_are_counted_and_ordered():
    ev = build_evaluation("r_test", frame(PAIRS), TIERS)

    assert ev.confusions == [
        ("a", "b", 2),  # the only pair seen twice
        ("b", "c", 1),  # then the singles, alphabetically by gold then predicted
        ("c", OTHER, 1),
        ("d", INVALID, 1),
        (OTHER, "a", 1),
    ]
    assert build_evaluation("r_test", frame(PAIRS), TIERS, top=2).confusions == [
        ("a", "b", 2),
        ("b", "c", 1),
    ]


def test_no_confusions_when_everything_is_right():
    ev = build_evaluation("r_test", frame([("a", "a"), (OTHER, OTHER)]), TIERS)

    assert ev.confusions == []
    assert "None: every prediction matched" in render_summary(ev)


def test_precision_and_recall_per_label():
    ev = build_evaluation("r_test", frame(PAIRS), TIERS)
    scores = {s.label: s for s in ev.per_label}

    assert list(scores) == ["a", "b", "c", "d", OTHER]
    # a: predicted in rows 1,2,13 (2 right); gold in rows 1-4 (2 found).
    assert scores["a"].precision == Ratio(2, 3)
    assert scores["a"].recall == Ratio(2, 4)
    assert scores["b"].precision == Ratio(1, 3)  # predicted b: rows 3,4,6
    assert scores["b"].recall == Ratio(1, 2)
    assert scores["c"].precision == Ratio(0, 1)  # predicted c once, wrongly
    assert scores["c"].recall == Ratio(0, 1)
    assert scores["d"].precision == Ratio(1, 1)
    assert scores["d"].recall == Ratio(1, 2)
    assert scores[OTHER].precision == Ratio(3, 4)  # predicted other: rows 7,10,11,12
    assert scores[OTHER].recall == Ratio(3, 4)


def test_zero_denominators_are_not_errors():
    ev = build_evaluation("r_test", frame([("a", "a")]), TIERS)
    scores = {s.label: s for s in ev.per_label}

    assert ev.other_share == Ratio(0, 0)
    assert scores["b"].precision == Ratio(0, 0)  # never predicted
    assert scores["b"].recall == Ratio(0, 0)  # never in gold


def test_confusion_matrix_shape_and_cells():
    ev = build_evaluation("r_test", frame(PAIRS), TIERS)
    matrix = ev.matrix

    assert list(matrix.index) == ["a", "b", "c", "d", OTHER]
    assert list(matrix.columns) == ["a", "b", "c", "d", OTHER, INVALID]
    assert matrix.index.name == "gold_label"
    assert matrix.loc["a", "b"] == 2
    assert matrix.loc["d", INVALID] == 1
    assert matrix.loc[OTHER, OTHER] == 3
    assert int(matrix.to_numpy().sum()) == 13


@pytest.mark.parametrize(
    ("bad", "message"),
    [
        (frame([("zzz", "a")]), "gold_label has labels not in intents.yaml"),
        (frame([("a", "zzz")]), "predicted has labels not in intents.yaml"),
        (frame([]), "no predictions"),
        (frame([("a", "a")]).drop(columns=["model"]), "missing columns"),
    ],
)
def test_read_predictions_rejects_bad_files(tmp_path, bad, message):
    path = tmp_path / "predictions.csv"
    bad.to_csv(path, index=False)

    with pytest.raises(ValueError, match=message):
        read_predictions(path, LABELS)


def test_load_tiers_rejects_an_unknown_tier(tmp_path):
    path = tmp_path / "intents.yaml"
    path.write_text("intents:\n  - {name: a, tier: B}\n  - {name: b, tier: Z}\n")

    with pytest.raises(ValueError, match="tier must be one of"):
        load_tiers(path)


def make_run(results_dir, run_id, pairs, mtime):
    run = results_dir / run_id
    run.mkdir(parents=True)
    frame(pairs).to_csv(run / "predictions.csv", index=False)
    os.utime(run / "predictions.csv", (mtime, mtime))


def test_latest_run_id_is_the_newest_predictions_file(tmp_path):
    make_run(tmp_path, "zzz_old_name_but_old_file_dev", PAIRS, mtime=1_000)
    make_run(tmp_path, "aaa_new_file_test", PAIRS, mtime=2_000)
    (tmp_path / "empty_run_dir").mkdir()  # no predictions.csv: ignored

    assert latest_run_id(tmp_path) == "aaa_new_file_test"


def test_latest_run_id_with_no_runs(tmp_path):
    with pytest.raises(ValueError, match="no runs"):
        latest_run_id(tmp_path)


def test_evaluate_run_on_missing_run(tmp_path):
    with pytest.raises(ValueError, match="no predictions.csv"):
        evaluate_run("nope_dev", results_dir=tmp_path)


@pytest.mark.parametrize(
    ("run_id", "banner"),
    [
        ("20261101T000000Z_v1_test", "TEST slice: these are the headline numbers."),
        ("20261101T000000Z_v1_dev", "DEV slice: for prompt development"),
        ("20261101T000000Z_v1_dev_n20", "Partial run: only the first 20 queries."),
        ("20261101T000000Z_v1_test_n20", "a partial run (only the first 20 queries)"),
        ("custom", "Slice unknown"),
    ],
)
def test_summary_says_whether_the_numbers_are_headline(tmp_path, run_id, banner):
    make_run(tmp_path, run_id, PAIRS, mtime=1_000)

    summary = render_summary(
        evaluate_run(run_id, results_dir=tmp_path, intents_path=intents(tmp_path))
    )

    assert banner in summary
    assert ("these are the headline numbers" in summary) == run_id.endswith("_test")


def intents(tmp_path):
    path = tmp_path / "intents.yaml"
    path.write_text(
        "intents:\n"
        + "".join(f"  - {{name: {k}, tier: {v}}}\n" for k, v in TIERS.items())
    )
    return path


def test_write_outputs_puts_the_counts_next_to_the_percentages(tmp_path):
    make_run(tmp_path, "20261101T000000Z_v9_test", PAIRS, mtime=1_000)
    ev = evaluate_run(
        "20261101T000000Z_v9_test", results_dir=tmp_path, intents_path=intents(tmp_path)
    )

    summary_path, confusion_path = write_outputs(ev, tmp_path / ev.run_id)
    summary = summary_path.read_text(encoding="utf-8")

    assert "| Intent accuracy, in-scope queries | 4 of 9 (44.4%) |" in summary
    assert (
        "| Out-of-scope queries correctly labelled `other` | 3 of 4 (75.0%) |"
        in summary
    )
    assert "| Tier accuracy, all queries | 8 of 13 (61.5%) |" in summary
    assert "| `a` | `b` | 2 |" in summary
    assert "| `a` | 2 of 3 (66.7%) | 2 of 4 (50.0%) |" in summary
    assert "prompt v9" in summary and "f" * 64 in summary
    # every percentage in the file is preceded by its counts
    percent_cells = [cell for cell in summary.split("|") if "%" in cell]
    assert percent_cells
    assert all(" of " in cell for cell in percent_cells)

    matrix = pd.read_csv(confusion_path, index_col="gold_label")
    assert matrix.loc["a", "b"] == 2
    assert matrix.shape == (5, 6)
