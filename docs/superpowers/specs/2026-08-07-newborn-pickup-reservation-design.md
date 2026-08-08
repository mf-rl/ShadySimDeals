# Newborn Pickup Reservation Design

## Goal

Prevent another caregiver from picking up a newborn between the completed
natural put-down and the seller's native Check On pickup. Preserve infant and
all downstream sale behavior.

## Root cause

The natural carrier finish correctly restores the newborn to an unparented,
routable state. Native Check On queues for the seller, but it does not reserve
the newborn immediately. The newborn caregiver situation can therefore queue
the mother's autonomous pickup first. Seller Check On then finishes
unnaturally without persistent Held Actions, and the transaction cancels.

The first reservation implementation acquired the seller's reservation inside
the mother's finishing callback. Live evidence showed that callback runs before
EA removes the mother's interaction reservation. Seller acquisition is
therefore rejected even though the newborn is already unparented.

That rejection also exposed an application-ordering defect. The pickup adapter
can report failure synchronously, but `TransactionOrchestrator` previously
entered `rabbit_hole_started` only after `run()` returned. Its synchronous
callback was ignored while the transaction was still `player_confirmed`,
leaving the transaction registry reservation active and hiding the newborn
from the next picker.

EA's `Baby` object participates in the standard object reservation system.
`ReservationHandlerBasic` excludes reservations from other Sims while allowing
interactions owned by the reserving Sim to use the same target.

The latest live diagnostic exposed an earlier branch in the failure. The
newborn reported no `parent` or initial carrier, while Cassandra still owned a
`ReservationHandlerUseList` and a `ReservationHandlerBasic` for Held Actions
(`275181`). Carrier detection trusted `parent`, so it skipped the natural
Held Actions finish and attempted the seller reservation immediately. Waiting
one tick cannot release an interaction that was never asked to finish.

## Design

Keep the existing newborn-only flow in
`Sims4RabbitHoleAdapter._queue_infant_pickup`:

1. Resolve the carrier from the newborn's `parent` when it is a Sim. If the
   parent is absent or is not a Sim, inspect the newborn's active reservation
   handlers for a foreign Sim's interaction whose affordance is Held Actions
   (`275181`). Ignore seller-owned and unrelated reservations.
2. If another Sim carries or reserves the newborn through Held Actions, finish
   that exact interaction with `FinishingType.NATURAL` and wait for the visible
   put-down. If neither source exists, retain the existing uncarried path.
3. After the carrier's finishing callback, schedule the remaining handoff on
   EA's simulation timeline with `sleep_until_next_tick_element()`. This lets
   the carrier interaction finish releasing its reservation before seller
   acquisition runs.
4. Immediately before queueing seller Check On on that next tick, create a
   `ReservationHandlerBasic` for the seller and newborn and begin the
   reservation.
5. If reservation acquisition fails or raises, cancel the pickup without
   queueing Check On.
6. Queue native Check On (`275655`). The seller's interaction may use the target
   because it belongs to the same Sim as the reservation.
7. Release the reservation after Check On finishes, whether it succeeds,
   cancels, or fails to create. Also release it when startup raises.
8. Start the existing seller-only rabbit hole only after Check On finishes
   naturally, seller Held Actions (`275181`) targets the newborn, and the
   newborn is parented to the seller.

Before calling any rabbit-hole adapter, `TransactionOrchestrator` transitions
the transaction from `player_confirmed` to `rabbit_hole_started`. A synchronous
adapter callback can then complete or fail through the normal cleanup path. If
the callback changes the state before `run()` returns, the orchestrator returns
that result without processing the adapter return value a second time.

The reservation is never held beyond the pickup boundary and does not disable
autonomy globally or mutate newborn parenting or state.

## Failure handling

Every terminal path after reservation acquisition releases it exactly once.
Failure to acquire or an exception while releasing is logged and cancels the
transaction before transfer or payment. EA's successful release returns
`None`, so only exceptions signal release failure. Existing transaction cleanup
remains responsible for sale reservations; the newborn object reservation is
local to pickup.

Failure to schedule the next-tick continuation cancels the pickup through the
same transaction callback. Synchronous adapter failures release transaction
participants and notify once; they cannot leave a target filtered from a later
picker.

Reservation inspection is read-only. Missing or malformed handlers are ignored;
the existing seller reservation attempt remains the authoritative gate and
fails cleanly if another owner still blocks the newborn. No reservation is
removed, replaced, or force-released.

## Testing

- Require reservation acquisition before Check On is pushed.
- Require the carrier-finish path to wait one simulation tick before seller
  reservation acquisition.
- With `parent` absent, resolve a foreign Held Actions (`275181`) reservation,
  naturally finish its exact interaction, and defer seller reservation until
  the next tick.
- Ignore unrelated reservations, and preserve the existing seller-held path
  when Held Actions belongs to the seller.
- Model a competing caregiver reservation and verify it is rejected while the
  seller owns the reservation.
- Verify cleanup after successful Check On, unnatural finish, rejected startup,
  and exceptions.
- Verify a synchronous rabbit-hole adapter failure reaches terminal state,
  releases transaction participants, and invokes completion once.
- Keep carried and uncarried newborn tests passing.
- Keep native infant pickup and handoff tests unchanged and passing.
- Keep the live checklist pending until the seller carries the newborn into the
  rabbit hole, the newborn leaves the household and lot, and one payment is
  deposited.

## Scope

- No changes to infant, toddler-through-elder, or unborn flows.
- No custom animation, carry implementation, autonomy disabling, or manual
  object parenting.
- No changes to pricing, transfer, consequences, payment, or rabbit-hole
  duration.
