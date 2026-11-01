> **Generated file: do not edit by hand.** Written by `phase0_resolvability/make_report.py` from `phase0_resolvability/report_template.md` and the saved runs; change the template, then run `make report`.

# Phase 0: which support tickets could an AI agent resolve?

## Findings

<!-- YOU WRITE THIS -->

## How I scored the intents

Every score is 1, 2 or 3, and 3 is always better for a bot (risk 3 = low risk).

| Intent | data_api | action | policy_clarity | risk | ambiguity | Tier |
|---|---|---|---|---|---|---|
| `lost_or_stolen_card` | 3 | 2 | 2 | 1 | 2 | B |
| `passcode_forgotten` | 3 | 3 | 3 | 1 | 3 | B |
| `card_arrival` | 2 | 2 | 1 | 2 | 2 | B |
| `card_swallowed` | 1 | 2 | 1 | 1 | 3 | C |
| `activate_my_card` | 3 | 3 | 3 | 2 | 3 | A |
| `order_physical_card` | 3 | 3 | 3 | 3 | 3 | A |
| `pin_blocked` | 2 | 2 | 3 | 1 | 2 | B |
| `change_pin` | 3 | 3 | 3 | 1 | 3 | B |
| `age_limit` | 3 | 3 | 3 | 1 | 3 | B |
| `edit_personal_details` | 3 | 2 | 3 | 2 | 2 | A |
| `declined_card_payment` | 2 | 2 | 2 | 2 | 1 | B |
| `transaction_charged_twice` | 2 | 1 | 2 | 1 | 1 | C |
| `request_refund` | 1 | 2 | 2 | 1 | 1 | C |
| `cancel_transfer` | 3 | 2 | 3 | 1 | 2 | B |
| `terminate_account` | 3 | 3 | 3 | 1 | 3 | B |

### `lost_or_stolen_card`

The agent can access clear lost / stolen card policies easily, however resolutions aren't standard to all cases. Therefore, policy clarity is 2. The actions to resolve are usually multiple, and a wrong answer/failure can lead to serious money/security harm. Most customer messages are straightforward, however the underlying meaning could be difficult to pinpoint. Risk is 1, therefore human intervention may be required.

### `passcode_forgotten`

The agent can easily access password entry data and reset process information. The step to resolve a forgotten password is simple, provide the reset password + verification process/link. The rules on what to do are clear, and the underlying meaning of messages is easy to pinpoint. However, a wrong answer/action resulting in bank password leakage or other security issues carries a high risk.

### `card_arrival`

Delivery & order tracking data most likely does not sit inside a bank system, making it difficult for the agent to access that data unless access is provided. The action is moderately clear as the agent has to check order tracking data if it can. Resolutions are case by case, as card arrival issues could have multiple external root causes/rules on what to do. Majority of the ticket needs are easy to pinpoint, however card_delivery_estimate is hard to differentiate when processing 'when will i get my card' requests. The allocated tier is B, as if data access is provided, the agent can easily read order/delivery data and resolve most queries, however, a human will be required if data access is not provided.

### `card_swallowed`

Almost all support tickets are physical/ATM related. The facts needed to understand the root cause are usually not in the bank system, especially if it's a physical defect. The action is moderately clear if no resolution is found - to contact the closest bank and get a human-in-the-loop. The resolution is dealt case by case as root causes can vary. The tickets are not ambiguous in terms of identifying the problem, but a wrong answer can lead to security harm or a lost card, thus the tier is C.

### `activate_my_card`

The agent can easily access identity, card and banking details from IAM, CMS and bank system APIs. Activating a card is a straightforward task with a clear policy, but a wrong answer/action can result in customers being restricted from their own card.

### `order_physical_card`

The agent can easily access information relating to how to order a physical card, which is what majority of the tickets are. The action is clear, usually one-step to return answers. The rules for ordering cards are well defined, the risk is low as a wrong answer is unlikely to lead to security/money harm, but rather a customer not able to order their card. Most tickets have the same wording & terminology.

### `pin_blocked`

The agent can access how many times a customer entered the wrong pin, and can access KYC/identity confirmation data, but cannot access actual PINs. There are multiple steps to resolving this issue, however they are well-defined steps (PIN-reset, identity check). These outcomes are detailed policies with minimal potential root causes: fraud or genuine PIN reset requirement. However, as fraudulent actors can prompt inject to request an agent for access to customer funds, the risk is high and therefore requires human intervention. Ambiguity is moderate as a few tickets are hard to label between get_physical_card and passcode_forgotten (if PIN/passcode terms are never used).

### `change_pin`

The agent can easily access the change pin process information. The rule to resolve change pin information tickets is clear. Ambiguity is low as tickets clearly point towards change_pin. The risk of a wrong answer/action is high as customers can lose access to funds. Therefore, the allocated tier is B as human oversight may be required for complex tickets.

### `age_limit`

The agent can easily access age limit data and open accounts. The actions to return age limit information is clear and simple, with rules on consent, age, child protection being very clear. Majority of the support tickets are not ambiguous as there's no in depth underlying meaning. The risk is high as a wrong answer can lead to a minor having an account when they're not supposed to, thus human oversight may be required. 

### `edit_personal_details`

The agent can access customer personal details easily, however there are multiple actions to editing personal details accurately. The rules on how to edit personal details and KYC/identity verification are straightforward. Most tickets don't specify details or labels, hence are moderately ambigious. The risk is moderate if an agent inaccurately edits details or provides misleading answers.

### `declined_card_payment`

The agent can easily read customer fund data, lost/stolen card status, spending limits, etc. However, it cannot read merchant network failures, especially for online shopping. The risk is moderate as wrong answers can lead to customer frustration. The support tickets could have multiple intents, thus a human-in-the-loop may be required for tickets that are not caused by the common causes (insufficient funds, stolen card status, etc).

### `transaction_charged_twice`

The agent cannot access/read/understand merchant data, human errors, network or system failures, however it can read the transaction and bank dispute routes. There is no clear action, and the policy on resolving transaction charged twice is only applicable if the root cause is internal such as authorization holds. The risk is high as funds can be lost, and the support tickets are ambiguous, hence the tier is C.

### `request_refund`

The agent can't access merchant refund policies or rules, this means there's no clear refunding action. The resolving action would be to request the customer to contact the merchant, thus the 2 score. The rule on what to do is unclear at the start, however the agent can fallback to asking the customer to contact the merchant. A bot promising refund or inventing merchant policy is high risk. Most support tickets don't mention the product, purchase amount, merchant, merchant refund policy, therefore the tickets are ambiguous. The tier is C and requires human intervention.

### `cancel_transfer`

The agent can easily access customer transaction data and KYC/identity verification data. However, reverting a transaction or verifying identity to prevent fraud is a multi-step process with variables. The rules on what to do when a customer is allowed to cancel/revert a transaction are well defined, but the risk of a bot cancelling real transactions or recommending false information is a security/money risk. Thus, the tier is B and may require human oversight. The intents pending_transfer, failed_transfer, and declined_transfer are tellable as they ask why, however there is some request_refund overlap, making it moderately ambiguous.

### `terminate_account`

The agent can easily achieve identity confirmation + KYC to confirm account cancellation. Closing an account is simple and has well defined rules, however is high risk if identity is not verified or the bot provides false answers. Majority of the support tickets were upset customers, thus customer frustration is an added business risk. Wording and terminology is similiar in most tickets, and they are tellable from other intents.

## Before and after the prompt change

- Before: `20261101T084927Z_v1_test` (prompt v1, TEST slice, 800 queries)
- After: `20261101T103105Z_v3_test` (prompt v3, TEST slice, 800 queries)

| Metric | Before | After | Change |
|---|---|---|---|
| Intent accuracy, in-scope queries | 564 of 600 (94.0%) | 579 of 600 (96.5%) | +2.5 pp |
| Out-of-scope queries correctly labelled `other` | 154 of 200 (77.0%) | 171 of 200 (85.5%) | +8.5 pp |
| Tier accuracy, all queries | 720 of 800 (90.0%) | 753 of 800 (94.1%) | +4.1 pp |

## Top confusions

From the After run `20261101T103105Z_v3_test` (TEST slice, 800 queries): gold label against predicted label, most frequent first.

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

## Why the confusions happen

<!-- YOU WRITE THIS -->

## What AI cannot resolve yet

<!-- YOU WRITE THIS -->

## Limits

- BANKING77 is a curated, balanced dataset, so its intent mix is not real traffic and no volume figure here is a measurement.
- Gold labels are intents, not tiers; tier accuracy inherits each intent's tier from my scoring.
