# Phase 0 evaluation: 20261101T103105Z_v3_test

**TEST slice: these are the headline numbers.**

- Run: `20261101T103105Z_v3_test` (prompt v3, sha256 `fa101de0b726b9b15b80dd73860cdbfd38352a84f8083259d073001f9f48fa1b`, model claude-haiku-5-5)
- Source: `results/phase0/20261101T103105Z_v3_test/predictions.csv`, 800 queries
- Command: `uv run python -m phase0_resolvability.evaluate 20261101T103105Z_v3_test`

## Results

| Metric | Result |
|---|---|
| Intent accuracy, in-scope queries | 579 of 600 (96.5%) |
| Out-of-scope queries correctly labelled `other` | 171 of 200 (85.5%) |
| Tier accuracy, all queries | 753 of 800 (94.1%) |
| Invalid predictions (counted as wrong everywhere) | 0 of 800 (0.0%) |

## 10 most frequent confusions

| Gold | Predicted | Count |
|---|---|---|
| `other` | `declined_card_payment` | 13 |
| `pin_blocked` | `other` | 6 |
| `other` | `order_physical_card` | 5 |
| `other` | `card_arrival` | 4 |
| `cancel_transfer` | `other` | 2 |
| `other` | `lost_or_stolen_card` | 2 |
| `other` | `passcode_forgotten` | 2 |
| `other` | `request_refund` | 2 |
| `pin_blocked` | `change_pin` | 2 |
| `activate_my_card` | `lost_or_stolen_card` | 1 |

## Per-label precision and recall

| Label | Precision | Recall |
|---|---|---|
| `lost_or_stolen_card` | 39 of 43 (90.7%) | 39 of 40 (97.5%) |
| `passcode_forgotten` | 40 of 42 (95.2%) | 40 of 40 (100.0%) |
| `card_arrival` | 39 of 44 (88.6%) | 39 of 40 (97.5%) |
| `card_swallowed` | 40 of 41 (97.6%) | 40 of 40 (100.0%) |
| `activate_my_card` | 38 of 38 (100.0%) | 38 of 40 (95.0%) |
| `order_physical_card` | 38 of 43 (88.4%) | 38 of 40 (95.0%) |
| `pin_blocked` | 31 of 31 (100.0%) | 31 of 40 (77.5%) |
| `change_pin` | 40 of 42 (95.2%) | 40 of 40 (100.0%) |
| `age_limit` | 40 of 41 (97.6%) | 40 of 40 (100.0%) |
| `edit_personal_details` | 39 of 39 (100.0%) | 39 of 40 (97.5%) |
| `declined_card_payment` | 40 of 53 (75.5%) | 40 of 40 (100.0%) |
| `transaction_charged_twice` | 40 of 40 (100.0%) | 40 of 40 (100.0%) |
| `request_refund` | 38 of 41 (92.7%) | 38 of 40 (95.0%) |
| `cancel_transfer` | 37 of 38 (97.4%) | 37 of 40 (92.5%) |
| `terminate_account` | 40 of 40 (100.0%) | 40 of 40 (100.0%) |
| `other` | 171 of 184 (92.9%) | 171 of 200 (85.5%) |

## How to read this

- Intent accuracy: of the queries whose gold label is an in-scope intent, how many got exactly that intent.
- Tier accuracy: a query is correct when the tier of its gold label equals the tier of its predicted label.
  Tiers come from `intents.yaml`; `other` has tier `none`; an `invalid` prediction has no tier and is always wrong.
  It counts every query, in-scope and `other`, so a wrong intent inside the right tier still counts as correct.
- Precision of a label: correct predictions of it out of all predictions of it. Recall: correct predictions of it out of all gold queries of it. `n/a` means 0 of 0.
- Confusions are gold/predicted pairs that disagree; ties are listed alphabetically.
- `confusion.csv` is the full matrix: one row per gold label, one column per predicted label, plus an `invalid` column.
