# Phase 0 evaluation: 20261101T084927Z_v1_test

**TEST slice: these are the headline numbers.**

- Run: `20261101T084927Z_v1_test` (prompt v1, sha256 `3c34a4800a607e38b647789d70c81e3967d4f9707ad32b65d5be0e2f6143401f`, model claude-haiku-5-5)
- Source: `results/phase0/20261101T084927Z_v1_test/predictions.csv`, 800 queries
- Command: `uv run python -m phase0_resolvability.evaluate 20261101T084927Z_v1_test`

## Results

| Metric | Result |
|---|---|
| Intent accuracy, in-scope queries | 564 of 600 (94.0%) |
| Out-of-scope queries correctly labelled `other` | 154 of 200 (77.0%) |
| Tier accuracy, all queries | 720 of 800 (90.0%) |
| Invalid predictions (counted as wrong everywhere) | 0 of 800 (0.0%) |

## 10 most frequent confusions

| Gold | Predicted | Count |
|---|---|---|
| `other` | `declined_card_payment` | 15 |
| `other` | `cancel_transfer` | 10 |
| `order_physical_card` | `card_arrival` | 6 |
| `other` | `card_arrival` | 5 |
| `other` | `order_physical_card` | 5 |
| `cancel_transfer` | `other` | 4 |
| `cancel_transfer` | `request_refund` | 4 |
| `other` | `lost_or_stolen_card` | 4 |
| `other` | `request_refund` | 4 |
| `request_refund` | `other` | 4 |

## Per-label precision and recall

| Label | Precision | Recall |
|---|---|---|
| `lost_or_stolen_card` | 39 of 44 (88.6%) | 39 of 40 (97.5%) |
| `passcode_forgotten` | 40 of 40 (100.0%) | 40 of 40 (100.0%) |
| `card_arrival` | 38 of 49 (77.6%) | 38 of 40 (95.0%) |
| `card_swallowed` | 40 of 41 (97.6%) | 40 of 40 (100.0%) |
| `activate_my_card` | 38 of 39 (97.4%) | 38 of 40 (95.0%) |
| `order_physical_card` | 32 of 37 (86.5%) | 32 of 40 (80.0%) |
| `pin_blocked` | 34 of 34 (100.0%) | 34 of 40 (85.0%) |
| `change_pin` | 40 of 44 (90.9%) | 40 of 40 (100.0%) |
| `age_limit` | 37 of 37 (100.0%) | 37 of 40 (92.5%) |
| `edit_personal_details` | 39 of 39 (100.0%) | 39 of 40 (97.5%) |
| `declined_card_payment` | 40 of 55 (72.7%) | 40 of 40 (100.0%) |
| `transaction_charged_twice` | 40 of 40 (100.0%) | 40 of 40 (100.0%) |
| `request_refund` | 35 of 43 (81.4%) | 35 of 40 (87.5%) |
| `cancel_transfer` | 32 of 43 (74.4%) | 32 of 40 (80.0%) |
| `terminate_account` | 40 of 40 (100.0%) | 40 of 40 (100.0%) |
| `other` | 154 of 175 (88.0%) | 154 of 200 (77.0%) |

## How to read this

- Intent accuracy: of the queries whose gold label is an in-scope intent, how many got exactly that intent.
- Tier accuracy: a query is correct when the tier of its gold label equals the tier of its predicted label.
  Tiers come from `intents.yaml`; `other` has tier `none`; an `invalid` prediction has no tier and is always wrong.
  It counts every query, in-scope and `other`, so a wrong intent inside the right tier still counts as correct.
- Precision of a label: correct predictions of it out of all predictions of it. Recall: correct predictions of it out of all gold queries of it. `n/a` means 0 of 0.
- Confusions are gold/predicted pairs that disagree; ties are listed alphabetically.
- `confusion.csv` is the full matrix: one row per gold label, one column per predicted label, plus an `invalid` column.
