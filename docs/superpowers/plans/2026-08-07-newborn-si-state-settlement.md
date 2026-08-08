# Newborn SI-State Settlement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Start newborn Check On only after the caregiver's Held Actions SI has fully exited, then settle pickup only after Check On has fully left the seller's SI state and its native Held Actions continuation exists.

**Architecture:** Keep the fix inside the existing newborn branch of `Sims4RabbitHoleAdapter._queue_infant_pickup`. Replace both premature interaction-finishing callbacks with native `SIState` watchers keyed to exact interaction removal. Defer work by one game tick after each removal notification to avoid starting or settling interactions reentrantly while EA is mutating SI state. Reuse the existing reservation, Held Actions lookup, completion callback, and failure logging; infant and sale behavior after pickup remain unchanged.

**Tech Stack:** Python 3.7-compatible Sims 4 script code, EA `SIState` watcher API, EA timeline elements, pytest under Python 3.12, PowerShell build/install scripts.

## Global Constraints

- Change production behavior only inside the `target_age == "baby"` path.
- Use `SIState.add_watcher` and `SIState.remove_watcher`; do not poll or add fixed multi-tick delays.
- Watch exact interaction identity, not affordance ID alone.
- Schedule one next-tick continuation after caregiver removal and one next-tick settlement after Check On removal.
- Do not force-release reservations, disable autonomy, mutate newborn parenting, or implement custom carry behavior.
- Preserve infant pickup `271032`, infant handoff `269721`, Check On `275655`, and Held Actions `275181`.
- Remove watchers outside EA's live notification iteration and release the seller reservation exactly once; a settlement-scheduling failure leaves its guarded watcher inert rather than mutating the watcher dictionary reentrantly.
- Keep live newborn completion pending until the complete sale passes in game.
- Commit and push reviewed changes to existing PR #7 without collaborator or AI attribution.

---

### Task 1: Wait for full caregiver Held Actions removal

**Files:**
- Modify: `tests/test_sims4_adapters.py:830-1570`
- Modify: `src/shady_sim_deals/sims4_adapters.py:548-860`
- Modify: `docs/superpowers/plans/2026-08-07-newborn-si-state-settlement.md`

**Interfaces:**
- Consumes: `carrier.si_state.add_watcher(handle, callback)` and `remove_watcher(handle)`.
- Produces: unchanged `_queue_infant_pickup(actor, target, callback) -> bool`.

- [x] **Step 1: Give the newborn test fixture a minimal observable SI state**

Add this test-only fake near `carried_infant_handoff_environment` and use it for
the fixture's seller and caregiver Sims:

```python
class FakeSIState:
    def __init__(self, *interactions):
        self.interactions = list(interactions)
        self.watchers = {}

    def __iter__(self):
        return iter(self.interactions)

    def add_watcher(self, handle, callback):
        self.watchers[handle] = callback
        return handle

    def remove_watcher(self, handle):
        return self.watchers.pop(handle)

    def set_interactions(self, *interactions):
        self.interactions[:] = interactions
        for watcher in self.watchers.values():
            watcher(self)
```

Initialize `Sim.si_state = FakeSIState()` in the fixture. Replace newborn-test
assignments such as `env.mother.si_state = [env.interaction]` with
`env.mother.si_state.set_interactions(env.interaction)`. Keep the separate
infant-only fixture unchanged.

- [x] **Step 2: Write the caregiver-removal regression first**

In `test_carried_newborn_is_released_then_held_by_seller`, preserve the natural
carrier cancel, but require that its early finishing callback cannot start the
handoff:

```python
env.finishing_callbacks[0](env.interaction)
assert env.scheduled_elements == []

env.mother.si_state.set_interactions()
assert len(env.scheduled_elements) == 1
```

Add or adapt focused tests for:

- unrelated SI-state changes while the exact Held Actions interaction remains;
- watcher registration failure canceling the pickup;
- carrier cancel failure removing the watcher and canceling the pickup;
- watcher removal failure canceling rather than starting Check On;
- unnatural carrier completion and a newborn still parented to the caregiver
  canceling after exact SI removal.

Rename `test_newborn_natural_release_exception_unregisters_finishing_callback`
to describe SI-state watcher cleanup. Remove assertions that require production
registration of a carrier finishing callback.

- [x] **Step 3: Run the focused test and verify RED**

Run:

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests\test_sims4_adapters.py -k "carried_newborn or parentless_newborn or newborn_release or newborn_handoff_schedule"
```

Expected: the new timing assertion fails because current production schedules
Check On from `register_on_finishing_callback`, before the exact carrier SI is
removed.

- [x] **Step 4: Replace the carrier finishing callback with one SI-state watcher**

In the foreign-carrier path, register a watcher before calling natural cancel.
Use the exact `held_interaction` already resolved from parenting or the foreign
Held Actions reservation:

```python
carrier_si_state = carrier.si_state
carrier_watcher = object()
carrier_done = False

def carrier_state_changed(si_state):
    nonlocal carrier_done
    if carrier_done or held_interaction in si_state:
        return
    carrier_done = True
    sequence = element_utils.build_element(
        (element_utils.sleep_until_next_tick_element(), finish_carrier_exit)
    )
    timeline = services.time_service().sim_timeline
    timeline.schedule(sequence, timeline.now)

def finish_carrier_exit(_timeline=None):
    try:
        carrier_si_state.remove_watcher(carrier_watcher)
    except Exception:
        callback(True)
        return
    if (
        not held_interaction.is_finishing_naturally
        or getattr(target_sim, "parent", None) is carrier
    ):
        callback(True)
        return
    queue_check_on()

carrier_si_state.add_watcher(carrier_watcher, carrier_state_changed)
held_interaction.cancel(
    FinishingType.NATURAL,
    cancel_reason_msg="Shady Sim Deals newborn handoff",
)
```

Wrap watcher registration and natural cancel in the existing failure boundary.
If cancel raises after registration, remove the watcher before reporting failure.
Do not retain `register_on_finishing_callback` or
`unregister_on_finishing_callback` in this newborn carrier path.

- [x] **Step 5: Run focused tests and verify GREEN**

Run the command from Step 3. Expected: all selected tests pass, including the
existing foreign-reservation carrier identification and infant controls selected
by their current names.

- [x] **Step 6: Commit the caregiver lifecycle boundary**

```powershell
git add src/shady_sim_deals/sims4_adapters.py tests/test_sims4_adapters.py docs/superpowers/plans/2026-08-07-newborn-si-state-settlement.md
git commit -m "fix: wait for newborn carrier exit"
```

---

### Task 2: Settle Check On after full seller SI removal

**Files:**
- Modify: `tests/test_sims4_adapters.py:992-1500`
- Modify: `src/shady_sim_deals/sims4_adapters.py:650-810`
- Modify: `docs/superpowers/plans/2026-08-07-newborn-si-state-settlement.md`

**Interfaces:**
- Consumes: seller `SIState` watcher notifications and the existing next-tick
  timeline helper.
- Produces: pickup success only when native Held Actions `275181` targets the
  newborn and `target.parent is actor` after Check On fully exits.

- [x] **Step 1: Make fake Check On participate in seller SI state**

Update the newborn fixture's `push_super_affordance` fake so the returned Check
On interaction is inserted into `actor.si_state`. Tests then remove that exact
interaction with `set_interactions(...)` to model `SIState._remove_gen()`.

Keep `scheduled_elements` as the observable timeline queue. The carrier removal
must append the first next-tick element; Check On removal must append the second.

- [x] **Step 2: Write settlement-boundary regressions first**

Update `test_carried_newborn_is_released_then_held_by_seller` to prove all four
boundaries:

```python
# Carrier SI removal schedules Check On startup.
env.mother.si_state.set_interactions()
env.scheduled_elements[0][1]()
check_on = env.actor.si_state.interactions[0]

# Merely entering finishing state does not settle or release.
check_on.is_finishing_naturally = True
assert callbacks == []
assert not any(event[0] == "ended" for event in env.reservation_events)

# Exact Check On removal schedules settlement; it does not settle reentrantly.
held = SimpleNamespace(
    affordance=SimpleNamespace(guid64=275181), target=env.carry_target
)
env.carry_target.parent = env.actor
env.actor.si_state.set_interactions(held)
assert callbacks == []
assert len(env.scheduled_elements) == 2

# The settlement tick observes EA's native continuation and succeeds once.
env.scheduled_elements[1][1]()
assert callbacks == [False]
assert env.reservation_events[-1] == (
    "ended", env.actor, env.carry_target
)
```

Add or adapt tests proving:

- unrelated seller SI changes do not settle while exact Check On remains;
- exact Check On removal without Held Actions cancels on the settlement tick;
- unnatural Check On removal cancels even if Held Actions exists;
- Held Actions for another target cancels;
- seller watcher registration, removal, or settlement scheduling exceptions
  release the reservation once and cancel pickup;
- repeated watcher notifications schedule and settle at most once.

Replace obsolete `test_newborn_callback_registration_exception...` and
`test_newborn_finishing_exception...` coverage with watcher registration and
settlement exceptions. Do not preserve tests for the removed early finishing
callback mechanism.

- [x] **Step 3: Run focused tests and verify RED**

Run:

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests\test_sims4_adapters.py -k "newborn and (check_on or reservation or carried or parented)"
```

Expected: new tests fail because current production settles directly from Check
On's early finishing callback and has no seller SI-state watcher.

- [x] **Step 4: Register the seller watcher before pushing Check On**

Inside `queue_check_on`, keep the existing reservation acquisition and central
`finish(canceled)` function. Add only local state and an idempotent watcher
cleanup helper:

```python
seller_si_state = actor_sim.si_state
seller_watcher = object()
seller_watcher_active = False
check_on_interaction = None
settlement_scheduled = False

def remove_seller_watcher():
    nonlocal seller_watcher_active
    if not seller_watcher_active:
        return True
    try:
        seller_si_state.remove_watcher(seller_watcher)
    except Exception:
        return False
    seller_watcher_active = False
    return True
```

Make `finish` call `remove_seller_watcher()` before releasing the reservation;
any cleanup failure forces `canceled=True`. Register the watcher before
`push_super_affordance` so an immediate SI-state transition cannot be missed.

- [x] **Step 5: Schedule settlement only when exact Check On leaves SI state**

Use the existing next-tick element mechanism rather than adding a timer or loop:

```python
def settle_check_on(_timeline=None):
    held_interaction = find_held_actions(actor_sim)
    succeeded = (
        check_on_interaction.is_finishing_naturally
        and held_interaction is not None
        and held_interaction.target is target_sim
        and getattr(target_sim, "parent", None) is actor_sim
    )
    log_event(
        "newborn_check_on_settled",
        naturally=check_on_interaction.is_finishing_naturally,
        held_actions_active=held_interaction is not None,
        parent_matches=getattr(target_sim, "parent", None) is actor_sim,
    )
    finish(not succeeded)

def seller_state_changed(si_state):
    nonlocal settlement_scheduled
    if (
        check_on_interaction is None
        or check_on_interaction in si_state
        or settlement_scheduled
    ):
        return
    settlement_scheduled = True
    element = element_utils.build_element(
        (element_utils.sleep_until_next_tick_element(), settle_check_on)
    )
    services.time_service().sim_timeline.schedule(element)
```

After assigning `check_on_interaction = result.interaction`, call
`seller_state_changed(seller_si_state)` once to cover an interaction that left
SI state during startup. Remove the old Check On
`register_on_finishing_callback`. Keep all exception paths routed through
`finish(True)` so the watcher and reservation are each cleaned up once. The
settlement-scheduling exception calls `finish(True, remove_watcher=False)` to
avoid mutating EA's live watcher dictionary during notification; its guarded
watcher is inert after reservation cleanup.

- [x] **Step 6: Run focused and full automated tests**

Run:

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests\test_sims4_adapters.py -k "newborn or native_infant_pickup or carried_infant"
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider
```

Expected: focused controls pass, then the complete suite passes with no newborn,
infant, pregnancy, payment, or rabbit-hole regressions.

- [x] **Step 7: Commit the seller settlement boundary**

```powershell
git add src/shady_sim_deals/sims4_adapters.py tests/test_sims4_adapters.py docs/superpowers/plans/2026-08-07-newborn-si-state-settlement.md
git commit -m "fix: settle newborn pickup after SI exit"
```

---

### Task 3: Align documentation, review, package, and install

**Files:**
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`
- Modify: `DEVELOPMENT.md`
- Modify: `SPECS_CHECKLIST.md`
- Modify: `docs/superpowers/plans/2026-08-07-newborn-si-state-settlement.md`

- [x] **Step 1: Align implementation-state documentation**

Update the newborn lifecycle descriptions to say:

- caregiver release is accepted only after the exact Held Actions SI leaves the
  caregiver's SI state;
- Check On result is evaluated only after the exact Check On SI leaves the
  seller's SI state and one settlement tick gives native Held Actions time to
  appear;
- live newborn sale remains pending until the seller carries the newborn into
  the rabbit hole and the newborn disappears from household and lot.

Mark the automated SI-state lifecycle checklist item complete only after the
full test suite passes. Preserve the latest failed live result as historical
evidence rather than claiming the live issue fixed.

- [x] **Step 2: Build the mod and inspect the archive**

```powershell
py -3.12 build_mod.py
tar -tf dist\ShadySimDeals.ts4script
```

Expected: build succeeds and the archive contains the updated
`shady_sim_deals/sims4_adapters.pyc` with the normal package modules.

- [x] **Step 3: Review the complete PR diff and run final verification**

Review all session work since the user-specified base commit:

```powershell
git diff --check bb78c4821c24faaf544557b0a120c817170bae4a
git diff --stat bb78c4821c24faaf544557b0a120c817170bae4a
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider
git status --short
```

Use `superpowers:requesting-code-review` for the base-to-HEAD diff. Resolve any
correctness finding, rerun affected tests and the full suite, then recheck the
diff. Do not add collaborator or AI attribution.

- [x] **Step 4: Commit docs, push PR #7, and verify remote state**

```powershell
git add README.md ARCHITECTURE.md DEVELOPMENT.md SPECS_CHECKLIST.md docs/superpowers/plans/2026-08-07-newborn-si-state-settlement.md
git commit -m "docs: record newborn SI settlement"
git push
gh pr checks 7
```

Verify every change after `bb78c4821c24faaf544557b0a120c817170bae4a` is in
the PR diff and the worktree is clean.

- [x] **Step 5: Install only while the game is closed**

Confirm `TS4_x64.exe` is not running, then run:

```powershell
.\install_mod.ps1
```

Report the installed artifact and request this focused live retest:

1. Start with seller outside the newborn's lot and caregiver holding newborn.
2. Select newborn and accept the deal.
3. Verify caregiver puts newborn down.
4. Verify seller enters the lot, completes native Check On/pickup, and carries
   newborn into the rabbit hole.
5. Verify newborn disappears from household and lot and payment is deposited
   once.
6. Attach the latest `ShadySimDeals.log` if any step fails.

---

## Plan Self-Review

- The plan fixes the two verified premature lifecycle boundaries instead of
  changing routing, autonomy, parenting, or reservation ownership.
- Exact interaction identity prevents unrelated SI changes from advancing the
  sale.
- Each watcher is registered before the transition it observes; removal occurs
  outside EA's live notification iteration, with scheduler failure leaving an
  inert guarded watcher after exact-once reservation cleanup.
- Each SI notification schedules work once on the next tick, avoiding reentrant
  EA SI-state mutation without introducing polling.
- Success still requires native Held Actions targeting the newborn plus seller
  parenting, so downstream rabbit-hole and payment behavior remain protected.
- The production change remains confined to the existing newborn branch and
  adds no dependency or reusable abstraction.
