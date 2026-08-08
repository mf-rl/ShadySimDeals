# Newborn Pickup Reservation Design

## Goal

Prevent another caregiver from picking up a newborn between the completed
natural put-down and the seller's native Check On pickup. Preserve infant and
all downstream sale behavior.

## Root cause

The newborn can be restored visibly to its cradle and become usable after the
carrier interaction fully exits. Native Check On can then continue into seller
Held Actions. The implementation does not wait for either full lifecycle
boundary.

EA bytecode confirms that `register_on_finishing_callback` reports the start of
finishing, not completion. `Interaction.cancel()` calls
`InteractionFinisher.on_finishing_move()`, which invokes finishing callbacks
immediately. Only later does `SIState._remove_gen()` run the interaction's full
`_exit()`, remove it from `_super_interactions`, release its reservations, and
notify SI-state watchers. A one-tick delay measured from the finishing callback
can therefore expire while Held Actions is still exiting.

Check On has the same two-phase lifecycle. Its finishing callback runs before
the interaction has exited and before its native Held Actions continuation is
available. The adapter currently checks seller parenting and Held Actions at
that early callback, cancels the sale, and releases its reservation even when
Check On finishes naturally. Live evidence shows Check On finishing naturally
with `parent=None` and no Held Actions observed at that premature check.

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
3. Before requesting the carrier finish, add a watcher to the carrier's
   `SIState`. Continue only after the exact Held Actions interaction is absent
   from that state, proving EA completed `_exit()` and released its interaction
   reservations. Because EA iterates its live watcher dictionary during state
   notification, defer watcher removal to the next-tick continuation; remove it
   immediately only when startup fails outside notification.
4. After full carrier removal, schedule the remaining handoff on EA's
   simulation timeline with `sleep_until_next_tick_element()` to avoid running
   seller startup reentrantly inside the carrier's state notification.
5. Immediately before queueing seller Check On on that next tick, create a
   `ReservationHandlerBasic` for the seller and newborn and begin the
   reservation.
6. If reservation acquisition fails or raises, cancel the pickup without
   queueing Check On.
7. Add a watcher to the seller's `SIState`, then queue native Check On
   (`275655`). The seller's interaction may use the target
   because it belongs to the same Sim as the reservation.
8. Do not settle from Check On's finishing callback. When the seller watcher
   observes that the exact Check On interaction has left `SIState`, wait one
   simulation tick for its continuation to enter the state.
9. On that settlement tick, succeed only if Check On finished naturally,
   seller Held Actions (`275181`) targets the newborn, and the newborn is
   parented to the seller. Otherwise cancel the pickup.
10. Remove the seller watcher and release the reservation exactly once on
    success, cancellation, failed startup, or exception. If scheduling the
    settlement itself fails inside EA's live watcher notification, release and
    cancel once while leaving the guarded watcher inert; removing it there would
    corrupt EA's dictionary iteration.
11. Start the existing seller-only rabbit hole only after verified seller carry
    ownership.

Before calling any rabbit-hole adapter, `TransactionOrchestrator` transitions
the transaction from `player_confirmed` to `rabbit_hole_started`. A synchronous
adapter callback can then complete or fail through the normal cleanup path. If
the callback changes the state before `run()` returns, the orchestrator returns
that result without processing the adapter return value a second time.

The reservation is never held beyond the pickup boundary and does not disable
autonomy globally or mutate newborn parenting or state.

## Failure handling

Every normal terminal path after reservation acquisition removes the seller
watcher and releases the reservation exactly once. A settlement-scheduling
failure inside EA's live watcher notification releases and cancels once but
leaves the watcher inert, because mutation during `notify_dirty()` raises.
Failure to acquire or an exception while releasing is logged and cancels the
transaction before transfer or payment. EA's successful release returns
`None`, so only exceptions signal release failure. Existing transaction cleanup
remains responsible for sale reservations; the newborn object reservation is
local to pickup.

Carrier watcher registration happens before natural cancellation so immediate
state changes cannot be missed. Registration failure cancels before requesting
the interaction finish. Watcher-removal failure is logged while terminal
reservation and transaction cleanup continue. Watchers are event-driven and
scoped to the exact interaction; there is no fixed multi-tick delay, indefinite
polling, or global autonomy change.

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
- Require the carrier-finish path to ignore the early finishing callback and
  wait until the exact interaction is removed from the carrier's `SIState`.
- Require seller reservation acquisition to occur no earlier than the next tick
  after full carrier removal.
- With `parent` absent, resolve a foreign Held Actions (`275181`) reservation,
  naturally finish its exact interaction, and defer seller reservation until
  the next tick.
- Ignore unrelated reservations, and preserve the existing seller-held path
  when Held Actions belongs to the seller.
- Model a competing caregiver reservation and verify it is rejected while the
  seller owns the reservation.
- Require Check On's early finishing callback to leave the transaction pending.
- After Check On leaves seller `SIState`, require one settlement tick before
  checking for its targeted Held Actions continuation and seller parenting.
- Verify a natural Check On without its continuation cancels only after the
  settlement tick; verify the continuation succeeds when it appears in time.
- Verify cleanup after successful Check On, unnatural finish, rejected startup,
  watcher failures, and exceptions.
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
