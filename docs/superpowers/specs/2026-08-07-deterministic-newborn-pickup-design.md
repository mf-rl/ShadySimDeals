# Deterministic Newborn Pickup Design

## Goal

Make a newborn sale deterministically place the newborn in the seller's native
Held Actions carry state before the existing seller-only rabbit hole begins.
Preserve the caregiver's visible natural put-down, EA routing and animation,
infant behavior, downstream transfer, and exact-once payment.

## Live Root Cause

The current adapter queues EA `baby_CheckOn_Minor` (`275655`) after the previous
carrier fully exits. The newest live run proves both SI-state watchers fire:
Check On queues, leaves the seller's SI state, and reaches the settlement tick.
At settlement, the newborn is still parentless and seller Held Actions is
absent.

EA tuning explains the result. Check On is a weighted need-response selector,
not a pickup contract. Some outcomes continue through `baby_HeldActions`
(`275181`) into held Cuddle, Rock, Bounce, Feed, or Shoosh actions. Other valid
outcomes choose Change Diaper (`13008`), Coo At (`8649`), or Talk (`77821`)
without a Held Actions override. Waiting longer cannot turn one of those
non-carry outcomes into pickup.

The same live event reports `is_finishing_naturally` as an empty list after full
SI removal. That value is not a reliable cross-boundary success signal. Native
targeted Held Actions plus newborn parenting is the authoritative carry proof.

## Chosen Architecture

Add one private, invisible interaction tuning resource:

- Name: `ShadySimDeals_NewbornPickup`
- Instance: `0xEAA21FFB1081E025`
- Type: interaction tuning `0xE882D22F`
- Actor/target: seller Sim and newborn `Baby` object
- Visibility: hidden, not user-directed, and not injected into any pie menu
- Routing constraints: copy the verified posture constraints from
  `baby_CheckOn_Minor`
- Basic content: one-shot staging interaction
- Outcome: exactly one continuation, EA `baby_Mixer_Cuddle` (`275239`), with
  `si_affordance_override` set to EA `baby_HeldActions` (`275181`)

This resource does not override or modify Check On, Cuddle, Held Actions, or any
other EA tuning. Only `Sims4RabbitHoleAdapter` requests it during a newborn sale.
The Cuddle continuation supplies EA's native routing, pickup animation,
parenting, and persistent carry super interaction without Check On's random
care-action selection.

## Alternatives Rejected

### Construct the mixer chain directly in Python

Pushing Held Actions and its Cuddle mixer manually would avoid one tuning
resource, but it couples the script to undocumented mixer-context and
super-interaction override internals. The private tuning expresses that native
relationship in the format EA already uses.

### Retry Check On until it chooses a held outcome

Retries remain nondeterministic and can repeatedly perform unrelated care
actions. They also complicate reservation lifetime and cancellation without
guaranteeing pickup.

### Return to `baby_HoldOut`

`baby_HoldOut` (`13011`) is a temporary bassinet interaction. It does not
establish the persistent carry ownership required for rabbit-hole travel.

## Transaction Flow

1. Resolve the newborn's active-zone `Baby` object from its household
   `SimInfo`.
2. Resolve an existing carrier from newborn parenting or a foreign Held Actions
   reservation.
3. If carried, request the carrier's exact Held Actions interaction to finish
   naturally. Wait for exact SI-state removal, then remove the watcher on the
   next simulation tick so EA's live watcher dictionary is not mutated during
   notification.
4. Acquire the existing seller-owned `ReservationHandlerBasic` for the newborn.
5. Register the existing seller SI-state watcher and push
   `ShadySimDeals_NewbornPickup` instead of `baby_CheckOn_Minor`.
6. When that exact private interaction leaves seller SI state, wait one
   settlement tick for its Cuddle continuation to enter Held Actions.
7. Succeed only when seller Held Actions (`275181`) targets the newborn and the
   newborn's parent is the seller. Do not require the unstable
   `is_finishing_naturally` value once ownership is proven.
8. Remove the seller watcher, release the reservation once, and start the
   existing seller-only 90-minute rabbit hole.
9. Keep transfer, return ordering, consequences, and payment unchanged.

## Failure Handling

Missing tuning, rejected push, absent targeted Held Actions, missing seller
parenting, reservation failure, watcher failure, or any exception cancels the
pickup. Cancellation starts no rabbit hole, transfers nobody, and pays nothing.

The existing callback and reservation guards retain exact-once terminal
behavior. The pathological timeline-scheduling failure remains unchanged: it
releases and cancels once while leaving the seller watcher inert rather than
mutating EA's watcher dictionary during notification.

## Implementation Scope

Production changes are limited to:

- one tuning XML resource under `tuning/interactions`;
- one package-resource entry and instance constant;
- replacing the newborn adapter's Check On interaction ID with the private
  pickup ID;
- changing settlement success to authoritative carry ownership rather than the
  unstable natural-finishing value;
- tests and maintained documentation.

No custom animation, manual parenting, autonomy override, routing override,
dependency, or infant-path change is introduced.

## Automated Verification

- Package resources contain interaction `0xEAA21FFB1081E025` exactly once.
- The tuning is invisible and not user-directed.
- The tuning has one and only one outcome continuation.
- That continuation is Cuddle `275239` with Held Actions override `275181`.
- The adapter requests the private interaction and no longer requests random
  Check On for newborn sales.
- Seller pickup remains pending until exact private-SI removal and one
  settlement tick.
- Targeted Held Actions plus seller parenting succeeds even when
  `is_finishing_naturally` is a non-Boolean falsey value.
- Missing or wrong-target Held Actions cancels and releases the reservation
  once.
- Existing carrier, reservation, infant pickup/handoff, rabbit-hole, transfer,
  and payment tests remain green.

## Live Acceptance Test

1. Begin with the seller outside the lot and another Sim carrying the newborn.
2. Select the newborn and accept the offer.
3. Confirm the caregiver visibly puts the newborn down.
4. Confirm the seller enters the lot, picks up/cuddles the newborn, and remains
   carrying it.
5. Confirm seller and newborn disappear together into the rabbit hole.
6. Confirm only the seller returns after 90 Sim minutes.
7. Confirm the newborn disappears from both household and lot and payment is
   deposited exactly once.
8. Confirm toddler, infant, child, adult, elder, and unborn sale behavior is
   unchanged.
