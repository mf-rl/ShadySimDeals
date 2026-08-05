# Household-Member Rabbit-Hole Design

## Goal

Run household-member sales through a real timed two-Sim rabbit hole. The seller
and target leave together; after the configured duration only the seller
returns, then the target transfers to ShadySimDeals Holdings and payment occurs.
Unborn-Nooboo sales remain immediate and outside this change.

## Verified integration

Patch 1.125.59.1030 exposes
RabbitHoleService.put_sims_in_shared_rabbithole for MultiSimRabbitHoleBase
subclasses. The built-in TwoSimRabbitHole maps the first Sim to actor
participants and the second to target participants. Its expiration callback
reports canceled=True for early removal, and duration comes from the selected
affordance's time-based exit condition.

Package three TwoSimRabbitHole tuning resources (type 0xB16AD2FA), each paired
with one private rabbit-hole affordance (type 0xE882D22F):

- Elder: 75 Sim minutes.
- Baby, infant, toddler, and child: 90 Sim minutes.
- Teen, young adult, and adult: 120 Sim minutes.

Use private instance IDs 0xEAA21FFB1081E005 through 0xEAA21FFB1081E00A.
The adapter selects the tuned rabbit-hole type from the target's age before
startup. Do not add these resources to phone, computer, or object affordance
injection lists.

## Transaction flow

The existing TransactionOrchestrator remains the ordering boundary, but its
rabbit-hole collaborator completes asynchronously:

1. Revalidate and reserve actor and target.
2. Start one shared rabbit hole with actor first and target second.
3. Transition to rabbit_hole_started only after startup and callback
   registration succeed.
4. Return control while both Sims remain in the managed rabbit hole.
5. On natural expiration, process the target, pay once, apply consequences,
   complete, release reservations, and notify the runtime callback.

The immediate no-op collaborator invokes the same callback synchronously, so
unborn behavior stays unchanged. No transfer or payment occurs at rabbit-hole
startup.

## Failure handling

Missing participants, rejected startup, or failed callback registration cancel
the shared request, fail the transaction, release reservations, and make no
target or funds changes. Early cancellation does the same. Failures after
target processing retain the existing transfer rollback and exactly-once
payment behavior.

The service returns both Sims before natural expiration is reported. The target
is transferred only from that callback, leaving only the seller selectable.

## Runtime and verification

Sims4RabbitHoleAdapter owns all patch-sensitive service, instance-manager,
callback, and SimInfo calls. Only the household workflow receives it. Household
completion and failure notifications move to the transaction-finished callback.

Automated tests cover age selection, shared participant order, delayed payment,
cancellation, startup failure, package resources, and injection isolation.
Live verification covers child, adult, and elder durations; both Sims leaving;
only the seller returning; target transfer; and exactly one payment. Checklist
live criteria remain unchecked until those in-game checks pass.
