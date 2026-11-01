<!-- report_template.md: the Phase 0 report. The {{NAME}} lines are filled by make_report.py.
     Why: my commentary is written in this file and the rest is generated; report.md is
     regenerated from it every time, so never edit report.md.
     Run: make report. This comment is dropped from report.md.
     Test: uv run pytest tests/test_make_report.py -->

# Phase 0: which support tickets could an AI agent resolve?

## Findings

Prompt v1 gave the classifier only the names of the 15 in-scope intents and `other`. Prompt v3 adds a one-line definition for each intent and for `other`. On the TEST slice, v1's main weakness was telling the in-scope intents apart from `other`, and v3 improved all three headline numbers: intent accuracy on in-scope queries rose from 564 of 600 (94.0%) to 579 of 600 (96.5%), +2.5 pp; out-of-scope queries correctly labelled `other` rose from 154 of 200 (77.0%) to 171 of 200 (85.5%), +8.5 pp; and tier accuracy rose from 720 of 800 (90.0%) to 753 of 800 (94.1%), +4.1 pp.

`cancel_transfer` showed the clearest gain: precision rose from 32 of 43 (74.4%) to 37 of 38 (97.4%). It sits next to several transfer intents that I left in `other` (my scoring notes already flag the overlap with pending, failed and declined transfers). In v1, 10 `other` queries were labelled `cancel_transfer`; in v3, none were.

The cost is more input tokens. The definitions add about 300 tokens to every call, roughly 240k across the 800 test queries, which is about $0.0241 more at Haiku 5.5 list price (v3 costs about 1.48x what v1 does).

v3 has its own problems. Out-of-scope queries are still pulled into in-scope intents, most often `declined_card_payment` (13 queries). `pin_blocked` also got worse: recall fell from 34 of 40 (85.0%) to 31 of 40 (77.5%), a drop of 3 queries (7.5 pp).

Each prompt was run once, so I have no repeat runs or confidence intervals, and a few queries out of 40 per intent is a small sample. I tuned the prompt on the DEV slice and used the TEST slice only to compare v1 and v3, so the reported numbers were not tuned on. They describe how the classifier behaves on this curated dataset, not on real traffic.

## How I scored the intents

{{INTENTS_TABLE}}

{{INTENT_WHYS}}

## Before and after the prompt change

{{COMPARISON}}

## Top confusions

{{CONFUSIONS}}

## Why the confusions happen

The mistakes cluster at the boundary between the 15 in-scope intents and `other`, not between the in-scope intents themselves: 8 of the 10 most frequent v3 confusions have `other` as the gold or predicted label.

`other` is not a random remainder. It is the 62 BANKING77 intents I did not score, and several are close neighbours of the 15. The queries pulled into `declined_card_payment` look like declined or failing-payment tickets from neighbouring intents (for example a virtual card or contactless payment not working), and those pulled into `order_physical_card` and `card_arrival` look like spare-card and delivery-estimate tickets. A person would also find these boundaries fuzzy, and the model has to draw them from a one-line definition.

A one-line definition fails in both directions. A broad one pulls neighbours in: "a card payment was declined or rejected" attracts other payment-failure tickets. A narrow one pushes real members out: `pin_blocked` is defined as a PIN blocked after too many wrong attempts, but its 9 misses include customers asking to reactivate or reinstate a PIN, or why they were blocked, and the `other` definition mentions finding a PIN.

My own scoring anticipated some of this: `card_arrival` and `cancel_transfer` both name the neighbouring intents they overlap with. It does not predict all of it, though. `transaction_charged_twice` has ambiguity 1 and was still 40 of 40 on both runs.

These explanations come from reading the errors in one run per prompt. I have not tested them, for example by rewriting a definition and rerunning.

## What AI cannot resolve yet

Recognising a ticket is not the same as resolving it. Tier accuracy of 753 of 800 (94.1%) says the classifier puts a ticket in the tier I assigned, not that an agent could finish it. Phase 0 tested no agent.

By my scoring, only 3 of the 15 in-scope intents are tier A (`activate_my_card`, `order_physical_card`, `edit_personal_details`), 9 are tier B and 3 are tier C. The tier C intents are the ones an agent cannot resolve alone. `card_swallowed` depends on facts that sit outside the bank's systems. `transaction_charged_twice` depends on merchant and network data and has no single clear action. `request_refund` depends on merchant refund policies the agent cannot see, and a bot promising a refund or inventing a policy is high risk.

Risk is the score that most often keeps an intent out of tier A. Ten of the 15 intents have risk 1, and four (`passcode_forgotten`, `change_pin`, `age_limit`, `terminate_account`) score 3 on everything else and are tier B only because a wrong answer could harm money or security. These are the tickets where I would keep a human check even though the data and policy are clear.

This covers only the 15 intents I scored, not the other 62. The scores are my judgement, not measurements. Real tickets are likely messier than BANKING77's curated one-intent queries, so I expect real-world accuracy to be lower than the figures above. These runs do not measure that.

## Limits

{{LIMITS}}
