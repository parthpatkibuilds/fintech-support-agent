# classify.py: asks the Claude classifier for the intent of every query in a slice CSV.
# Why: Phase 0 compares predicted and gold labels; every API call is cached on disk, so a
# rerun with the same model, prompt, text and settings costs nothing.
# Run: uv run python -m phase0_resolvability.classify data/slices/dev.csv --prompt phase0_resolvability/prompts/v1.txt --limit 20
# Test: uv run pytest tests/test_classify.py

import argparse
import hashlib
import json
import sys
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import anthropic
import pandas as pd

import config
from phase0_resolvability.sample import OTHER, load_intent_names

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "cache" / "classify"  # under data/, so gitignored
RESULTS_DIR = ROOT / "results" / "phase0"

# Request settings. Haiku 5.5 returns a 400 for temperature, top_p and top_k, so never send them.
EFFORT = "low"
THINKING = {"type": "disabled"}  # accepted by Haiku 5.5 at effort high or below
MAX_TOKENS = 256
INVALID = "invalid"

COLUMNS = [
    "text",
    "gold_label",
    "gold_in_scope",
    "predicted",
    "prompt_version",
    "prompt_sha",
    "model",
    "timestamp",
    "input_tokens",
    "output_tokens",
]


@dataclass(frozen=True)
class Prompt:
    version: str  # file name without .txt, e.g. v1
    text: str  # sent to the model exactly as read
    sha: str  # SHA-256 of that text


def read_prompt(path: Path) -> Prompt:
    # Text mode: CRLF and LF files give the same text, so the same hash.
    text = path.read_text(encoding="utf-8")
    return Prompt(path.stem, text, hashlib.sha256(text.encode("utf-8")).hexdigest())


def build_schema(labels: list[str]) -> dict:
    """JSON schema with one property, `intent`, that must be one of labels."""
    if len({label.lower() for label in labels}) != len(labels):
        raise ValueError(
            "two labels differ only by case; the case-insensitive match would be ambiguous"
        )
    return {
        "type": "object",
        "properties": {"intent": {"type": "string", "enum": labels}},
        "required": ["intent"],
        "additionalProperties": False,
    }


def request_settings(schema: dict) -> dict:
    return {
        "schema": schema,
        "effort": EFFORT,
        "thinking": THINKING,
        "max_tokens": MAX_TOKENS,
    }


def settings_digest(settings: dict) -> str:
    return hashlib.sha256(
        json.dumps(settings, sort_keys=True).encode("utf-8")
    ).hexdigest()


def map_label(raw: object, labels: list[str]) -> str:
    """Match the model's label to my list ignoring case; return my spelling or INVALID.

    The docs say enum values can come back with different capitalisation.
    """
    if isinstance(raw, str):
        for label in labels:
            if raw.lower() == label.lower():
                return label
    return INVALID


def predict(record: dict, labels: list[str]) -> str:
    """Turn one recorded API call into a label. Anything unusual is INVALID."""
    if record["stop_reason"] != "end_turn":  # max_tokens, refusal, ...
        return INVALID
    try:
        raw = json.loads(record["raw_text"])["intent"]
    except (TypeError, ValueError, KeyError):  # no text, not JSON, or no `intent`
        return INVALID
    return map_label(raw, labels)


def cache_path(
    cache_dir: Path, model: str, prompt_sha: str, text: str, digest: str
) -> Path:
    key = json.dumps([model, prompt_sha, text, digest])
    return cache_dir / f"{hashlib.sha256(key.encode('utf-8')).hexdigest()}.json"


def read_cache(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_cache(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(
        ".tmp"
    )  # write then rename, so a crash never leaves half a file
    temp.write_text(json.dumps(record), encoding="utf-8")
    temp.replace(path)


class Classifier:
    def __init__(
        self,
        client_factory: Callable[[], anthropic.Anthropic],
        model: str,
        prompt: Prompt,
        labels: list[str],
        cache_dir: Path = CACHE_DIR,
    ) -> None:
        self.client_factory = client_factory  # called only on the first cache miss
        self.model = model
        self.prompt = prompt
        self.labels = labels
        self.cache_dir = cache_dir
        self.settings = request_settings(build_schema(labels))
        self.digest = settings_digest(self.settings)
        self._client: anthropic.Anthropic | None = None
        self.api_calls = 0
        self.cache_hits = 0
        self.new_input_tokens = 0  # tokens billed by calls made in this run only
        self.new_output_tokens = 0
        self.stop_reasons: Counter[str] = Counter()

    def record(self, text: str) -> dict:
        """The recorded API call for this text: from disk if cached, else a new call."""
        path = cache_path(
            self.cache_dir, self.model, self.prompt.sha, text, self.digest
        )
        record = read_cache(path)
        if record is None:
            record = self._call(text)
            write_cache(path, record)
            self.api_calls += 1
            self.new_input_tokens += record["input_tokens"]
            self.new_output_tokens += record["output_tokens"]
        else:
            self.cache_hits += 1
        self.stop_reasons[record["stop_reason"]] += 1
        return record

    def _call(self, text: str) -> dict:
        if self._client is None:
            self._client = self.client_factory()
        response = self._client.messages.create(
            model=self.model,
            max_tokens=self.settings["max_tokens"],
            thinking=self.settings["thinking"],
            output_config={
                "effort": self.settings["effort"],
                "format": {"type": "json_schema", "schema": self.settings["schema"]},
            },
            system=self.prompt.text,
            messages=[{"role": "user", "content": text}],
        )
        raw_text = next((b.text for b in response.content if b.type == "text"), None)
        return {
            "model": self.model,
            "prompt_sha": self.prompt.sha,
            "text": text,
            "settings_digest": self.digest,
            "stop_reason": response.stop_reason,
            "raw_text": raw_text,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "request_id": getattr(response, "_request_id", None),
            "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        }


def classify_slice(slice_df: pd.DataFrame, classifier: Classifier) -> pd.DataFrame:
    rows = []
    total = len(slice_df)
    for number, (text, gold) in enumerate(
        zip(slice_df["text"], slice_df["gold_label"]), 1
    ):
        record = classifier.record(text)
        rows.append(
            {
                "text": text,
                "gold_label": gold,
                "gold_in_scope": gold != OTHER,
                "predicted": predict(record, classifier.labels),
                "prompt_version": classifier.prompt.version,
                "prompt_sha": classifier.prompt.sha,
                "model": record["model"],
                "timestamp": record["timestamp"],
                "input_tokens": record["input_tokens"],
                "output_tokens": record["output_tokens"],
            }
        )
        if number % 50 == 0 or number == total:
            print(f"  {number}/{total} done")
    return pd.DataFrame(rows, columns=COLUMNS)


def make_client() -> anthropic.Anthropic:
    if not config.ANTHROPIC_API_KEY:
        sys.exit("ANTHROPIC_API_KEY is not set. Put it in .env (see .env.example).")
    return anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, timeout=60.0)


def print_summary(predictions: pd.DataFrame, classifier: Classifier) -> None:
    invalid = int((predictions["predicted"] == INVALID).sum())
    reasons = ", ".join(f"{k}={v}" for k, v in sorted(classifier.stop_reasons.items()))
    print(
        f"\nQueries: {len(predictions)}  (API calls {classifier.api_calls}, cache hits {classifier.cache_hits})"
    )
    print(f"Invalid predictions: {invalid}")
    print(f"stop_reason: {reasons}")
    print(
        f"Tokens billed by this run's API calls: "
        f"input {classifier.new_input_tokens}, output {classifier.new_output_tokens}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify a slice CSV with Claude.")
    parser.add_argument("slice", type=Path, help="CSV with columns text, gold_label")
    parser.add_argument(
        "--prompt",
        type=Path,
        required=True,
        help="prompt file, e.g. phase0_resolvability/prompts/v1.txt",
    )
    parser.add_argument("--limit", type=int, help="classify only the first N rows")
    parser.add_argument("--run-id", help="folder name under results/phase0/")
    args = parser.parse_args()

    labels = [*load_intent_names(), OTHER]
    prompt = read_prompt(args.prompt)
    slice_df = pd.read_csv(args.slice, keep_default_na=False)
    if list(slice_df.columns) != ["text", "gold_label"]:
        sys.exit(
            f"{args.slice}: expected columns text, gold_label; got {list(slice_df.columns)}"
        )
    unknown = sorted(set(slice_df["gold_label"]) - set(labels))
    if unknown:
        sys.exit(
            f"{args.slice}: gold labels not in intents.yaml or `{OTHER}`: {unknown}"
        )
    if args.limit:
        slice_df = slice_df.head(args.limit)

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    suffix = f"_n{args.limit}" if args.limit else ""
    run_id = args.run_id or f"{stamp}_{prompt.version}_{args.slice.stem}{suffix}"
    out_dir = RESULTS_DIR / run_id
    out_dir.mkdir(parents=True)  # refuses to overwrite an existing run

    print(
        f"Model {config.MODEL_CLASSIFIER}, prompt {prompt.version} (sha256 {prompt.sha[:12]}...), {len(slice_df)} queries"
    )
    classifier = Classifier(make_client, config.MODEL_CLASSIFIER, prompt, labels)
    predictions = classify_slice(slice_df, classifier)
    path = out_dir / "predictions.csv"
    predictions.to_csv(path, index=False)
    print_summary(predictions, classifier)
    print(f"Wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
