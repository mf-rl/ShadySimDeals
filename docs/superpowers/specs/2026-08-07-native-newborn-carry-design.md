# Native Newborn Carry Design

## Goal

Make a carried newborn sale use The Sims 4's native newborn carry sequence so the seller carries the newborn into the rabbit hole. Preserve all existing infant, toddler-through-elder, and unborn sale behavior.

## Root cause

Newborns are `Baby` objects rather than normal instantiated Sims. The attempted `baby_HoldOut` interaction (`13011`) is a temporary bassinet interaction, not the persistent newborn carry interaction. Replacing it with native Check On correctly reaches the seller pickup path, but `cancel_user()` ends the mother's `baby_HeldActions` unnaturally and leaves the newborn parentless in an unroutable in-world state. Live diagnostics then show Check On queueing with no parent, canceling unnaturally, and never creating seller `baby_HeldActions`; the seller displays the game's routing-failure gesture.

EA's own service code distinguishes user cancellation from `cancel(FinishingType.NATURAL, ...)`. The `baby_HeldActions` tuning restores the InCrib state during its normal exit. The carrier must therefore complete the native natural put-down transition before the seller approaches.

## Design

Only the `target_age == "baby"` branch in `Sims4RabbitHoleAdapter._queue_infant_pickup` changes.

1. Resolve the newborn's `Baby` object through `services.object_manager()` as today.
2. If another Sim carries it, register a finishing callback on that Sim's active `baby_HeldActions` interaction and request `cancel(FinishingType.NATURAL, ...)`.
3. Wait for the complete visible put-down/restore-to-crib exit. Do not queue the seller while the mother still owns the newborn.
4. After natural completion, verify the newborn is no longer parented to the previous carrier, then queue EA's `baby_CheckOn_Minor` interaction (`275655`) for the seller and newborn. This is EA's native entry into the continuation whose super-interaction override is persistent `baby_HeldActions` (`275181`).
5. Confirm the seller has an active `baby_HeldActions` interaction targeting the newborn and owns the carried object before starting the existing seller-only rabbit hole.
6. Treat rejected natural completion, an unnatural carrier finish, Check On cancellation, or missing carry ownership as transaction cancellation. Transfer and payment remain downstream and unchanged.

The infant branch continues to use pickup `271032` or handoff `269721`. Rabbit-hole selection, transfer, pricing, payment, consequences, and every non-newborn age path remain unchanged.

## Testing

- Add a failing regression that requires `FinishingType.NATURAL` instead of `cancel_user()` and proves Check On is not queued until the carrier finishes naturally and no longer parents the newborn.
- Keep the existing Check On, targeted Held Actions, exception, rejected-transition, and ownership regressions passing.
- Keep the existing infant pickup and handoff tests unchanged and passing.
- Run the complete automated suite, build both mod artifacts, and install only after the game is closed.
- Keep the live newborn checklist pending until the seller visibly carries the newborn into the rabbit hole, the newborn disappears from the household and lot, and one payment is deposited.

## Non-goals

- No custom newborn animation or carry implementation.
- No manual object parenting or state mutation.
- No changes to infant or other sale flows.
- No changes outside the existing newborn branch and its tests or current-state documentation.
