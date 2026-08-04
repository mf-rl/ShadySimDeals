# Device-Use Animations Design

## Goal

Make all four ShadySimDeals entry points visibly use their selected device before
opening the existing picker:

- Phone household-member sale
- Phone unborn-Nooboo sale
- Computer household-member sale
- Computer unborn-Nooboo sale

Phone interactions animate in place. Computer interactions route to and use the
clicked computer. The offer, confirmation, target processing, payment, and
notification flows remain unchanged.

## Verified native sources

Reuse base-game interaction tuning from supported patch `1.125.59.1030`. During
implementation, extract the current game tuning and select:

- One user-directed phone browse/use interaction that creates and operates the
  phone without requiring a call recipient.
- One user-directed computer browse interaction that routes to a compatible
  computer, acquires its normal posture, and performs a short browsing cycle.

Copy only the routing, posture, constraints, and animation content required by
the ShadySimDeals interaction. Do not override the EA interaction or guess an
animation state-machine name. Record the exact source tuning names and instance
IDs in `DEVELOPMENT.md`. If no compatible native source can be verified, stop
the integration instead of shipping a simulated delay or an invented ID.

## Architecture

The existing four interaction classes and Lot51 injection remain unchanged.
Their XML resources receive device-specific native content:

- Both phone resources share the verified phone content.
- Both computer resources share the verified computer routing, posture, and
  animation content.

In `sims4_runtime.py`, household and unborn interactions expose their current
picker setup as `_open_picker()`. The shared `_ShadySimDealsInteraction` body
first delegates to `SuperInteraction._run_interaction_gen` so the tuned native
content runs, then calls `_open_picker()`.

Concrete phone and computer classes select the failure policy with a small class
attribute. This keeps sale-type behavior shared and avoids copying the same
device sequence into four Python methods.

## Runtime flow

### Phone

1. The queued ShadySimDeals interaction begins.
2. The Sim performs one native phone-use cycle in place.
3. The appropriate existing picker opens.
4. The interaction finishes; dialog callbacks continue the unchanged offer and
   transaction flow.

If native phone content raises or reports failure, log `device_animation_failed`
with the phone entry point and still open the picker. A cosmetic failure must
not disable an otherwise safe phone transaction.

### Computer

1. The queued ShadySimDeals interaction routes to the clicked computer.
2. The Sim acquires the native computer-use posture and performs one browsing
   cycle.
3. The appropriate existing picker opens.
4. The interaction finishes; dialog callbacks continue the unchanged offer and
   transaction flow.

If routing, posture acquisition, or native animation fails, log
`device_animation_failed` with the computer entry point and end the interaction
without opening the picker. The mod must not pretend an inaccessible computer
was used.

No artificial timer, loop, rabbit hole, or transaction mutation is part of this
feature.

## Safety and compatibility

- The interactions remain non-autonomous and non-saveable.
- Picker cancellation remains mutation-free.
- Device animation runs before any target selection, reservation, pregnancy
  change, household transfer, or payment.
- Phone and computer use only base-game tuning so no pack dependency is added.
- Lot51 Core remains the only mod dependency and continues to own affordance
  injection.
- The feature targets patch `1.125.59.1030`; source tuning must be rechecked after
  supported game patches.

## Automated verification

Tests will prove:

- Native device content completes before `_open_picker()` is called.
- Phone failure logs and falls back to the picker.
- Computer failure logs and suppresses the picker.
- Household and unborn interactions still share their respective picker and
  transaction implementations.
- Both phone XML resources contain the same verified phone device content.
- Both computer XML resources contain the same verified computer routing and
  animation content.
- The package index and Lot51 references remain unchanged apart from resource
  payload updates.

## Live verification

On patch `1.125.59.1030`:

1. Run both sale actions from the phone and confirm a phone-use animation occurs
   before each picker.
2. Run both actions from a reachable computer and confirm the Sim routes to and
   visibly uses that computer before each picker.
3. Make a computer inaccessible and confirm the queued action fails without
   opening a picker or changing game state.
4. Confirm picker cancellation remains harmless.
5. Complete one household and one unborn transaction to confirm both existing
   workflows still succeed.
6. Inspect `lastException.txt` and `shady_sim_deals.log`.

Only after these checks pass should **Computer-use and phone-use animations** be
marked complete in `SPECS_CHECKLIST.md`.

## Deferred work

Real rabbit holes, timed returns, seller buffs, relationship consequences,
pregnant-Sim reactions, and custom animation assets remain separate checklist
tasks.
