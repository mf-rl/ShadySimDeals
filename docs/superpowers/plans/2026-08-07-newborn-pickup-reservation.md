# Newborn Pickup Reservation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reserve a newly put-down newborn for the seller so caregiver autonomy cannot steal it before native Check On establishes seller carry ownership.

**Architecture:** Keep the existing newborn branch in `Sims4RabbitHoleAdapter._queue_infant_pickup`. Acquire an EA `ReservationHandlerBasic` immediately before pushing Check On, permit the same seller's interaction to use the target, and release the reservation through one cleanup callback on every Check On terminal path. Infant and downstream sale code remain unchanged.

**Tech Stack:** Python 3.7-compatible Sims 4 script code, EA object reservation API, pytest under Python 3.12, PowerShell build/install scripts.

## Global Constraints

- Change production behavior only inside the `target_age == "baby"` branch.
- Do not disable autonomy globally or mutate newborn parenting or state.
- Do not add dependencies, custom animations, or carry implementations.
- Preserve infant pickup `271032`, infant handoff `269721`, Check On `275655`, and Held Actions `275181`.
- Release the newborn object reservation on every terminal path after acquisition.
- Keep live newborn completion pending until the complete sale passes in game.
- Commit and push reviewed changes to existing PR #7 without collaborator or AI attribution.

---

### Task 1: Protect seller Check On with a newborn reservation

**Files:**
- Modify: `src/shady_sim_deals/sims4_adapters.py:574-704`
- Modify: `tests/test_sims4_adapters.py:830-1135`
- Modify: `README.md:27`
- Modify: `ARCHITECTURE.md:23`
- Modify: `DEVELOPMENT.md:19,39`
- Modify: `SPECS_CHECKLIST.md:106-110`
- Modify: `docs/superpowers/plans/2026-08-07-newborn-pickup-reservation.md`

**Interfaces:**
- Consumes: `ReservationHandlerBasic(sim, target)`, `begin_reservation() -> ReservationResult`, and `end_reservation() -> None` from EA's reservation API.
- Produces: unchanged `_queue_infant_pickup(actor, target, callback) -> bool`; callback receives `False` only after reservation cleanup and verified seller Held Actions.

- [x] **Step 1: Extend the newborn test environment with a fake EA reservation**

In `carried_infant_handoff_environment`, install a fake
`reservation.reservation_handler_basic` module. Record creation, acquisition,
and release without changing the infant fixtures:

```python
reservation_events = []

class ReservationHandlerBasic:
    def __init__(self, sim, target):
        self.sim = sim
        self.target = target
        reservation_events.append(("created", sim, target))

    def begin_reservation(self):
        reservation_events.append(("begun", self.sim, self.target))
        return True

    def end_reservation(self):
        reservation_events.append(("ended", self.sim, self.target))
```

Expose `reservation_events` from the returned environment.

- [x] **Step 2: Write failing acquisition, competition, and cleanup regressions**

Update `test_carried_newborn_is_released_then_held_by_seller` to require this
order before the carrier finishing callback returns:

```python
assert env.reservation_events == [
    ("created", env.actor, env.carry_target),
    ("begun", env.actor, env.carry_target),
]
assert env.requested_ids == [275655]
```

After successful Check On, require exactly one release before success:

```python
check_on_callbacks[0](check_on_interaction)
assert env.reservation_events[-1] == (
    "ended", env.actor, env.carry_target
)
assert callbacks == [False]
```

Add `test_newborn_reservation_blocks_competing_caregiver`, using a fake handler
whose `begin_reservation` marks the newborn reserved by `env.actor` and whose
`may_reserve(env.mother)` returns `False`; assert the competitor is rejected
while seller Check On remains queued.

Add `test_newborn_reservation_rejection_cancels_without_check_on`, making
`begin_reservation()` return `False`; assert `callbacks == [True]`,
`requested_ids == []`, and no release occurs.

Extend the existing Check On startup-exception and unnatural-finish tests to
assert one `ended` event. Add an acquisition-exception test where
`begin_reservation()` raises and assert Check On is not requested. Add
`test_newborn_reservation_release_exception_cancels_pickup`, make
`end_reservation()` raise after otherwise successful Check On, and assert the
pickup callback receives `True` rather than starting the rabbit hole.

- [x] **Step 3: Run focused tests and verify RED**

Run:

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests\test_sims4_adapters.py -k "newborn_reservation or carried_newborn_is_released or newborn_check_on_startup_exception or unnatural_newborn_release or native_infant_pickup or carried_infant"
```

Expected: reservation assertions fail because production does not import or
acquire `ReservationHandlerBasic`; existing infant controls pass.

- [x] **Step 4: Acquire and centrally release the newborn reservation**

Inside the newborn branch, import the EA handler:

```python
from reservation.reservation_handler_basic import ReservationHandlerBasic
```

At the start of `queue_check_on`, acquire it before requesting affordance
`275655`:

```python
try:
    reservation = ReservationHandlerBasic(actor_sim, target_sim)
    if not reservation.begin_reservation():
        failed("newborn_reservation_rejected")
        callback(True)
        return
except Exception:
    failed("newborn_reservation_exception")
    callback(True)
    return
```

Define one cleanup boundary in `queue_check_on`:

```python
reservation_released = False

def finish(canceled):
    nonlocal reservation_released
    if reservation_released:
        return
    reservation_released = True
    try:
        reservation.end_reservation()
    except Exception:
        failed("newborn_reservation_release_exception")
        callback(True)
        return
    callback(canceled)
```

EA's successful `end_reservation()` returns `None`; do not interpret its return
value as rejection. Only an exception signals release failure.

Replace every `callback(True)` inside `queue_check_on` after acquisition with
`finish(True)`. In `check_on_finished`, retain the existing natural-finish,
targeted Held Actions, and seller-parent checks, but pass their cancellation
result to `finish(...)` instead of calling `callback(...)` directly. Do not
change the carrier natural-put-down callback or any infant code.

- [x] **Step 5: Run focused tests and verify GREEN**

Run the Step 3 command. Expected: all selected newborn and infant tests pass.

- [x] **Step 6: Align maintained documentation with the failed live result and reservation flow**

- `README.md`, `ARCHITECTURE.md`, and `DEVELOPMENT.md`: say the seller reserves
  the newborn after the natural put-down and before Check On so another
  caregiver cannot reacquire it.
- `SPECS_CHECKLIST.md`: keep live newborn sale unchecked and record that the
  natural put-down passed, but the mother reacquired the newborn before seller
  Check On and both sale attempts canceled with **Inconvenient Fact**.

- [x] **Step 7: Verify, review, commit, push, and install**

Run:

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests
py -3.12 build_mod.py
git diff --check
```

Request read-only review over
`bb78c4821c24faaf544557b0a120c817170bae4a..HEAD` plus the working-tree change.
Fix all Critical and Important findings. Commit with conventional subject
`fix: reserve newborn for seller pickup`, push `fix/native-newborn-carry`, and
install only after The Sims 4 is closed.
