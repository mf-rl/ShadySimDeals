# Sale Rabbit-Hole Ordering Design

## Goal

Run every confirmed sale through a real rabbit hole before applying its target mutation or payment.

## Household-member flow

1. Reserve the actor and selected household member.
2. Start the existing age-based shared rabbit hole with the actor first and target second.
3. Leave household membership, sold markers, and funds unchanged while it runs.
4. On natural expiration, transfer the target to ShadySimDeals Holdings.
5. Deposit payment once and return only the actor.

The existing 75-, 90-, and 120-minute age durations remain unchanged.

## Unborn flow

1. Reserve the actor and selected pregnant Sim.
2. Select a duration from the public expected-offspring count: 90 minutes for one, 120 for twins, and 150 for triplets or more.
3. If actor and target are the same Sim, start a one-Sim rabbit hole. Otherwise start a shared two-Sim rabbit hole with actor first and pregnant Sim second.
4. Leave pregnancy and funds unchanged while the rabbit hole runs.
5. On natural expiration, safely conclude the selected pregnancy and deposit payment once.
6. Return every participant; the selected Sim is no longer pregnant.

## Architecture

Keep `TransactionOrchestrator` as the ordering boundary. Both transaction workflows receive asynchronous rabbit-hole collaborators and use the existing expiration callback before target processing. The Sims adapter selects household tuning by target age and unborn tuning by participant count and expected-offspring count.

Package the minimum private one-Sim and two-Sim unborn rabbit-hole resources needed for the three durations. Reuse each duration affordance between its one-Sim and two-Sim rabbit-hole definitions where the game tuning contract allows it.

## Failure handling

Rabbit-hole startup failure, callback-registration failure, or cancellation releases reservations without transferring a Sim, clearing a pregnancy, or paying funds. Validation runs again after natural expiration. Pregnancy processing retains the existing compensated-payment safety if the game API fails after payment begins.

## Verification

Automated tests must prove that household transfer, pregnancy conclusion, and payment do not occur at startup; natural expiration applies them in order; cancellation applies none; one-Sim and two-Sim unborn participant selection is correct; duration selection is correct; and all private resources are packaged without public affordance injection.

Live verification must cover one household sale, one self-target unborn sale, and one other-target unborn sale, including cancellation and exact payment ordering.
