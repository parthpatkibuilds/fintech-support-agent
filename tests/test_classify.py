# Tests for phase0_resolvability/classify.py: label mapping, the disk cache, request shape.
# Why: the classifier must map labels safely, never re-pay for a repeated call, and never send
# the parameters Haiku 5.5 rejects. A stub client stands in for the API; no real call is made.
# Run: uv run pytest tests/test_classify.py

import json
from types import SimpleNamespace

import pandas as pd
import pytest

from phase0_resolvability import classify
from phase0_resolvability.classify import (
    COLUMNS,
    INVALID,
    Classifier,
    Prompt,
    build_schema,
    cache_path,
    map_label,
    predict,
    read_prompt,
    request_settings,
    settings_digest,
)

LABELS = ["lost_or_stolen_card", "card_arrival", "other"]
PROMPT = Prompt("v1", "Pick an intent.", "a" * 64)


def reply(label: str | None, stop_reason: str = "end_turn", raw: str | None = None):
    """What the stub returns in place of an anthropic Message."""
    text = raw if raw is not None else json.dumps({"intent": label})
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        stop_reason=stop_reason,
        usage=SimpleNamespace(input_tokens=120, output_tokens=9),
        _request_id="req_stub",
    )


class StubClient:
    """Answers every query with `answer`, and remembers each request it received."""

    def __init__(self, answer=None):
        self.answer = answer or reply("card_arrival")
        self.requests: list[dict] = []
        self.messages = (
            self  # so the code under test can call client.messages.create(...)
        )

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return self.answer


@pytest.fixture(autouse=True)
def no_real_client(monkeypatch):
    def refuse():
        raise AssertionError("a test tried to create a real Anthropic client")

    monkeypatch.setattr(classify, "make_client", refuse)


def make_classifier(stub, tmp_path, model="claude-test", prompt=PROMPT):
    return Classifier(lambda: stub, model, prompt, LABELS, cache_dir=tmp_path / "cache")


# --- label mapping -----------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("card_arrival", "card_arrival"),
        ("Card_Arrival", "card_arrival"),  # capitalisation differs: use my spelling
        ("LOST_OR_STOLEN_CARD", "lost_or_stolen_card"),
        ("Other", "other"),
        ("card_swallowed", INVALID),  # not in my list
        ("card arrival", INVALID),  # not just a case difference
        (" card_arrival", INVALID),
        ("", INVALID),
        (None, INVALID),
        (7, INVALID),
        (["card_arrival"], INVALID),
    ],
)
def test_map_label(raw, expected):
    assert map_label(raw, LABELS) == expected


def test_schema_rejects_labels_that_differ_only_by_case():
    with pytest.raises(ValueError, match="differ only by case"):
        build_schema(["card_arrival", "Card_Arrival"])


def test_schema_has_one_property_enum_of_labels():
    schema = build_schema(LABELS)
    assert schema == {
        "type": "object",
        "properties": {"intent": {"type": "string", "enum": LABELS}},
        "required": ["intent"],
        "additionalProperties": False,
    }


@pytest.mark.parametrize(
    "stop_reason, raw_text, expected",
    [
        ("end_turn", '{"intent": "card_arrival"}', "card_arrival"),
        ("end_turn", '{"intent": "Card_arrival"}', "card_arrival"),
        ("end_turn", '{"intent": "nonsense"}', INVALID),
        ("end_turn", "not json", INVALID),
        ("end_turn", "{}", INVALID),
        ("end_turn", '["card_arrival"]', INVALID),
        ("end_turn", None, INVALID),  # no text block at all
        (
            "max_tokens",
            '{"intent": "card_arrival"}',
            INVALID,
        ),  # valid-looking but cut off
        ("refusal", '{"intent": "card_arrival"}', INVALID),
    ],
)
def test_predict(stop_reason, raw_text, expected):
    record = {"stop_reason": stop_reason, "raw_text": raw_text}
    assert predict(record, LABELS) == expected


# --- prompt hash -------------------------------------------------------------------


def test_prompt_hash_is_the_same_for_lf_and_crlf_files(tmp_path):
    lf = tmp_path / "v1.txt"
    crlf = tmp_path / "v2.txt"
    lf.write_bytes(b"line one\nline two\n")
    crlf.write_bytes(b"line one\r\nline two\r\n")

    assert read_prompt(lf).sha == read_prompt(crlf).sha
    assert read_prompt(lf).text == "line one\nline two\n"
    assert read_prompt(lf).version == "v1"


# --- cache -------------------------------------------------------------------------


def test_second_identical_call_comes_from_disk(tmp_path):
    stub = StubClient()
    first = make_classifier(stub, tmp_path)
    first.record("where is my card")
    assert len(stub.requests) == 1

    again = make_classifier(stub, tmp_path)  # a fresh object: only the disk is shared
    record = again.record("where is my card")

    assert len(stub.requests) == 1  # no second API call
    assert (first.api_calls, first.cache_hits) == (1, 0)
    assert (again.api_calls, again.cache_hits) == (0, 1)
    assert record["input_tokens"] == 120 and record["stop_reason"] == "end_turn"


def test_cache_needs_no_client_at_all(tmp_path):
    make_classifier(StubClient(), tmp_path).record("hello")

    def no_client():
        raise AssertionError("client should not be needed for a cached query")

    cached = Classifier(
        no_client, "claude-test", PROMPT, LABELS, cache_dir=tmp_path / "cache"
    )
    cached.record("hello")


@pytest.mark.parametrize(
    "model, prompt, text",
    [
        ("claude-other", PROMPT, "hello"),  # different model
        (
            "claude-test",
            Prompt("v1", "Pick an intent.", "b" * 64),
            "hello",
        ),  # different prompt sha
        ("claude-test", PROMPT, "hello!"),  # different text
    ],
)
def test_changing_any_key_part_is_a_cache_miss(tmp_path, model, prompt, text):
    stub = StubClient()
    make_classifier(stub, tmp_path).record("hello")
    make_classifier(stub, tmp_path, model=model, prompt=prompt).record(text)
    assert len(stub.requests) == 2


@pytest.mark.parametrize(
    "change",
    [
        {"effort": "high"},
        {"thinking": {"type": "adaptive"}},
        {"max_tokens": 512},
        {"schema": build_schema(LABELS[:2])},
    ],
)
def test_changing_any_request_setting_changes_the_cache_key(tmp_path, change):
    base = request_settings(build_schema(LABELS))
    changed = {**base, **change}
    assert settings_digest(changed) != settings_digest(base)
    one = cache_path(tmp_path, "m", "sha", "text", settings_digest(base))
    two = cache_path(tmp_path, "m", "sha", "text", settings_digest(changed))
    assert one != two


def test_refusals_and_cutoffs_are_cached_too(tmp_path):
    stub = StubClient(reply(None, stop_reason="refusal", raw="I can't help with that."))
    make_classifier(stub, tmp_path).record("hello")
    record = make_classifier(stub, tmp_path).record("hello")
    assert len(stub.requests) == 1
    assert record["stop_reason"] == "refusal"


# --- request shape -----------------------------------------------------------------


def test_request_has_exactly_the_agreed_settings(tmp_path):
    stub = StubClient()
    make_classifier(stub, tmp_path).record("my card has not arrived")
    (request,) = stub.requests

    # Haiku 5.5 returns a 400 for these, and it has no `fallbacks` parameter.
    for banned in ("temperature", "top_p", "top_k", "fallbacks", "betas", "tools"):
        assert banned not in request
    assert set(request) == {
        "model",
        "max_tokens",
        "thinking",
        "output_config",
        "system",
        "messages",
    }
    assert request["model"] == "claude-test"
    assert request["max_tokens"] == 256
    assert request["thinking"] == {"type": "disabled"}
    assert request["output_config"]["effort"] == "low"
    assert request["output_config"]["format"] == {
        "type": "json_schema",
        "schema": build_schema(LABELS),
    }
    assert request["system"] == PROMPT.text
    assert request["messages"] == [
        {"role": "user", "content": "my card has not arrived"}
    ]


# --- whole slice -------------------------------------------------------------------


def test_classify_slice_output_columns_and_counts(tmp_path):
    stub = StubClient(reply("Card_Arrival"))  # wrong case on purpose
    classifier = make_classifier(stub, tmp_path)
    slice_df = pd.DataFrame(
        {
            "text": ["where is my card", "what is the weather"],
            "gold_label": ["card_arrival", "other"],
        }
    )

    out = classify.classify_slice(slice_df, classifier, "dev")

    assert list(out.columns) == COLUMNS
    assert out["slice"].tolist() == ["dev", "dev"]
    assert out["predicted"].tolist() == ["card_arrival", "card_arrival"]
    assert out["gold_in_scope"].tolist() == [True, False]
    assert set(out["prompt_version"]) == {"v1"}
    assert set(out["prompt_sha"]) == {"a" * 64}
    assert set(out["model"]) == {"claude-test"}
    assert out["input_tokens"].tolist() == [120, 120]
    assert out["output_tokens"].tolist() == [9, 9]
    assert (classifier.new_input_tokens, classifier.new_output_tokens) == (240, 18)
    assert classifier.stop_reasons == {"end_turn": 2}
