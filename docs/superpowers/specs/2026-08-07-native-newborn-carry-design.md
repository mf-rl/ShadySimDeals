# Native Newborn Carry Design

## Goal

Make a carried newborn sale use The Sims 4's native newborn carry sequence so the seller carries the newborn into the rabbit hole. Preserve all existing infant, toddler-through-elder, and unborn sale behavior.

## Root cause

Newborns are `Baby` objects rather than normal instantiated Sims. The attempted `baby_HoldOut` interaction (`13011`) is a temporary bassinet interaction, not the persistent newborn carry interaction. Live diagnostics show it queues after the current carrier releases the newborn, then cancels unnaturally with no seller ownership or active `baby_HeldActions`; the seller displays the game's routing-failure gesture.

## Design

Only the `target_age == "baby"` branch in `Sims4RabbitHoleAdapter._queue_infant_pickup` changes.

1. Resolve the newborn's `Baby` object through `services.object_manager()` as today.
2. If another Sim carries it, cancel that Sim's active interaction targeting the newborn and wait for it to finish.
3. Queue EA's `baby_CheckOn_Minor` interaction (`275655`) for the seller and newborn. This is EA's native entry into the continuation whose super-interaction override is persistent `baby_HeldActions` (`275181`).
4. Confirm the seller has an active `baby_HeldActions` interaction targeting the newborn and owns the carried object before starting the existing seller-only rabbit hole.
5. Treat rejection, cancellation, or missing carry ownership as transaction cancellation. Transfer and payment remain downstream and unchanged.

The infant branch continues to use pickup `271032` or handoff `269721`. Rabbit-hole selection, transfer, pricing, payment, consequences, and every non-newborn age path remain unchanged.

## Testing

- Replace the newborn HoldOut regression with a failing test that requires `275655`, followed by active `275181` and seller ownership before the callback succeeds.
- Keep the existing infant pickup and handoff tests unchanged and passing.
- Run the complete automated suite, build both mod artifacts, and install only after the game is closed.
- Keep the live newborn checklist pending until the seller visibly carries the newborn into the rabbit hole, the newborn disappears from the household and lot, and one payment is deposited.

## Non-goals

- No custom newborn animation or carry implementation.
- No manual object parenting or state mutation.
- No changes to infant or other sale flows.
- No commit or push in this session.
