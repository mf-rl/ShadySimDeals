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
Repeating the sale loses the same race immediately; transaction reservations
are not stuck.

EA's `Baby` object participates in the standard object reservation system.
`ReservationHandlerBasic` excludes reservations from other Sims while allowing
interactions owned by the reserving Sim to use the same target.

## Design

Keep the existing newborn-only flow in
`Sims4RabbitHoleAdapter._queue_infant_pickup`:

1. If another Sim carries the newborn, finish that carrier's Held Actions with
   `FinishingType.NATURAL` and wait for the visible put-down.
2. Immediately before queueing seller Check On, create a
   `ReservationHandlerBasic` for the seller and newborn and begin the
   reservation.
3. If reservation acquisition fails or raises, cancel the pickup without
   queueing Check On.
4. Queue native Check On (`275655`). The seller's interaction may use the target
   because it belongs to the same Sim as the reservation.
5. Release the reservation after Check On finishes, whether it succeeds,
   cancels, or fails to create. Also release it when startup raises.
6. Start the existing seller-only rabbit hole only after Check On finishes
   naturally, seller Held Actions (`275181`) targets the newborn, and the
   newborn is parented to the seller.

The reservation is never held beyond the pickup boundary and does not disable
autonomy globally or mutate newborn parenting or state.

## Failure handling

Every terminal path after reservation acquisition releases it exactly once.
Failure to acquire or release is logged and cancels the transaction before
transfer or payment. Existing transaction cleanup remains responsible for sale
reservations; the newborn object reservation is local to pickup.

## Testing

- Require reservation acquisition before Check On is pushed.
- Model a competing caregiver reservation and verify it is rejected while the
  seller owns the reservation.
- Verify cleanup after successful Check On, unnatural finish, rejected startup,
  and exceptions.
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
