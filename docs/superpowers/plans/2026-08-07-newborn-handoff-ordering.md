# Newborn Handoff Ordering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let EA finish releasing the carrier's newborn reservation before the seller reserves it, and guarantee synchronous pickup failures clean up the sale transaction.

**Architecture:** Keep the existing native newborn put-down, seller reservation, Check On, and Held Actions flow. Defer only the post-put-down seller continuation by one EA simulation tick, and make the shared transaction orchestrator enter its callback-valid state before invoking any rabbit-hole adapter.

**Tech Stack:** Python 3.7-compatible Sims 4 script code, EA `element_utils`/simulation timeline, pytest on Python 3.12, PowerShell build/install scripts.

## Global Constraints

- Preserve infant, toddler-through-elder, and unborn behavior.
- Do not disable autonomy, clobber another Sim's reservation, mutate newborn parenting manually, or add custom carry behavior.
- Keep pricing, transfer, consequences, payment, and rabbit-hole durations unchanged.
- Every production behavior change must first have a failing regression test.
- Keep the live newborn checklist pending until the complete sale passes in game.

---

### Task 1: Make transaction callbacks safe during adapter startup

**Files:**
- Modify: `tests/test_transactions.py`
- Modify: `src/shady_sim_deals/orchestrator.py:44-67`

**Interfaces:**
- Consumes: `TransactionOrchestrator.confirm_and_complete(transaction, on_finished=None)` and rabbit-hole adapters exposing `run(transaction, on_finished)`.
- Produces: the same public method and return contract, with callbacks valid as soon as adapter startup begins.

- [x] **Step 1: Write the failing synchronous-cancellation regression**

Add this test to `tests/test_transactions.py`:

```python
def test_synchronous_rabbit_hole_cancellation_releases_once():
    events = []

    class SynchronousCancellation(Recorder):
        def run(self, transaction, on_finished):
            self.events.append("rabbit_hole")
            on_finished(canceled=True)
            return True

    completed = []
    workflow = TransactionOrchestrator(
        Recorder(events),
        Recorder(events),
        SynchronousCancellation(events),
        Recorder(events),
        Recorder(events),
        Recorder(events),
    )
    deal = transaction()
    workflow.prepare(deal, SaleOffer(5000, {}, "buyer"))

    assert not workflow.confirm_and_complete(deal, completed.append)
    assert deal.state == "failed"
    assert deal.failure_reason == "Rabbit hole was canceled"
    assert events.count("release") == 1
    assert completed == [deal]
```

- [x] **Step 2: Run the test and verify RED**

Run:

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests\test_transactions.py::test_synchronous_rabbit_hole_cancellation_releases_once
```

Expected: FAIL because the callback runs while the transaction is still `player_confirmed`; the state remains `rabbit_hole_started`, release is absent, and the observer is not called.

- [x] **Step 3: Implement callback-valid startup ordering**

In `TransactionOrchestrator.confirm_and_complete`, transition before `run()` and stop processing adapter startup if a synchronous callback already changed the state:

```python
self._states.transition(transaction, "player_confirmed")
callback = lambda canceled=False: self._finish_after_rabbit_hole(
    transaction, canceled, on_finished
)
self._states.transition(transaction, "rabbit_hole_started")
started = self._rabbit_holes.run(transaction, callback)
if transaction.state != "rabbit_hole_started":
    return transaction.state == "completed"
if started is False:
    raise TransactionError("Rabbit hole could not start")
```

Remove the old post-`run()` transition. Retain the existing `started is None` compatibility callback after the `try` block.

- [x] **Step 4: Run transaction tests and verify GREEN**

Run:

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests\test_transactions.py
```

Expected: all transaction tests pass; delayed and immediate completion behavior remains unchanged.

- [x] **Step 5: Commit the independently verified transaction fix**

```powershell
git add tests/test_transactions.py src/shady_sim_deals/orchestrator.py
git commit -m "fix: settle synchronous sale failures"
```

---

### Task 2: Defer seller reservation until the next simulation tick

**Files:**
- Modify: `tests/test_sims4_adapters.py:831-1059`
- Modify: `src/shady_sim_deals/sims4_adapters.py:548-742`

**Interfaces:**
- Consumes: EA `element_utils.build_element`, `element_utils.sleep_until_next_tick_element`, and `services.time_service().sim_timeline.schedule(element, when)`.
- Produces: unchanged `Sims4RabbitHoleAdapter._queue_infant_pickup(actor, target, callback) -> bool`; only the carried-newborn continuation becomes next-tick asynchronous.

- [x] **Step 1: Extend the fake game environment with a simulation timeline**

In `carried_infant_handoff_environment`, add `scheduled_elements = []`, a fake `element_utils` module, and a time service:

```python
next_tick = object()
element_utils = SimpleNamespace(
    build_element=lambda sequence: sequence,
    sleep_until_next_tick_element=lambda: next_tick,
)
timeline = SimpleNamespace(
    now=object(),
    schedule=lambda element, when: scheduled_elements.append(element),
)
services.time_service = lambda: SimpleNamespace(sim_timeline=timeline)
monkeypatch.setitem(sys.modules, "element_utils", element_utils)
```

Expose `next_tick` and `scheduled_elements` on the returned environment.

- [x] **Step 2: Change the carried-newborn test to require next-tick acquisition**

In `test_carried_newborn_is_released_then_held_by_seller`, immediately after invoking the mother's finishing callback, require no seller reservation or Check On yet:

```python
env.finishing_callbacks[0](env.interaction)
assert env.reservation_events == []
assert env.requested_ids == []
assert len(env.scheduled_elements) == 1
sleep, continue_handoff = env.scheduled_elements[0]
assert sleep is env.next_tick

continue_handoff()
assert env.reservation_events == [
    ("created", env.actor, env.carry_target),
    ("begun", env.actor, env.carry_target),
]
```

Keep the existing Check On, Held Actions, reservation release, and final callback assertions after this block.

- [x] **Step 3: Add a schedule-failure regression**

Add a test that replaces `services.time_service().sim_timeline.schedule` with a function raising `RuntimeError("schedule failed")`, naturally finishes the carrier interaction, and asserts `callbacks == [True]`, no reservation was created, and the logger records `baby_pickup_failed` with reason `newborn_handoff_schedule_exception`.

- [x] **Step 4: Run the focused tests and verify RED**

Run:

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests\test_sims4_adapters.py -k "carried_newborn_is_released or newborn_handoff_schedule"
```

Expected: the carried-newborn test fails because reservation acquisition is still immediate; the new schedule-failure test also fails because no scheduling boundary exists.

- [x] **Step 5: Implement the native next-tick continuation**

Import `element_utils` inside the newborn branch. Add this local function beside `queue_check_on`:

```python
def schedule_check_on():
    try:
        sequence = element_utils.build_element(
            (
                element_utils.sleep_until_next_tick_element(),
                queue_check_on,
            )
        )
        timeline = services.time_service().sim_timeline
        timeline.schedule(sequence, timeline.now)
    except Exception:
        failed("newborn_handoff_schedule_exception")
        callback(True)
```

In `carrier_finished`, retain the natural-finish and detached-parent checks, but call `schedule_check_on()` instead of `queue_check_on()`. Do not defer the already-unparented or seller-carried newborn paths, and do not change infant handoff code.

- [x] **Step 6: Run focused newborn and infant tests and verify GREEN**

Run:

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests\test_sims4_adapters.py -k "newborn or infant_pickup or carried_infant"
```

Expected: all selected tests pass, including unchanged infant controls.

- [x] **Step 7: Commit the independently verified handoff fix**

```powershell
git add tests/test_sims4_adapters.py src/shady_sim_deals/sims4_adapters.py
git commit -m "fix: defer newborn pickup reservation"
```

---

### Task 3: Align documentation, verify, review, push, and install

**Files:**
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`
- Modify: `DEVELOPMENT.md`
- Modify: `SPECS_CHECKLIST.md`
- Modify: `docs/superpowers/plans/2026-08-07-newborn-handoff-ordering.md`

**Interfaces:**
- Consumes: the verified behavior from Tasks 1 and 2.
- Produces: maintained documentation matching the tested implementation and latest live result.

- [ ] **Step 1: Record the implementation and live result accurately**

Update maintained docs to say the carried-newborn path waits one simulation tick after natural put-down before seller reservation and native Check On. Replace the current newborn checklist detail with:

```markdown
- [ ] Live: newborn appears and can be selected; the latest attempt stops after selection because seller reservation is rejected before Check On, and the synchronous failure leaves the newborn filtered from the next picker (next-tick handoff and transaction cleanup await validation)
```

Keep the overall newborn sale item unchecked.

- [ ] **Step 2: Run full verification**

Run:

```powershell
$testTemp = Join-Path (Get-Location) '.pytest_cache\task-temp'
New-Item -ItemType Directory -Force -Path $testTemp | Out-Null
$env:TEMP=$testTemp
$env:TMP=$testTemp
$env:PYTHONPATH='src'
py -3.12 -m pytest -q -p no:cacheprovider --basetemp .pytest_cache\pytest-task tests
py -3.12 build_mod.py
git diff --check
```

Expected: all tests pass, both `dist/ShadySimDeals.ts4script` and `dist/ShadySimDeals.package` build, and `git diff --check` is silent.

- [ ] **Step 3: Request read-only review**

Review the branch diff from `bb78c4821c24faaf544557b0a120c817170bae4a` through `HEAD` plus the working tree. Fix every Critical or Important finding and rerun the affected tests.

- [ ] **Step 4: Mark this plan complete and commit documentation**

Mark completed checkboxes in this plan, then run:

```powershell
git add README.md ARCHITECTURE.md DEVELOPMENT.md SPECS_CHECKLIST.md docs/superpowers/plans/2026-08-07-newborn-handoff-ordering.md
git commit -m "docs: record newborn handoff ordering"
```

- [ ] **Step 5: Push and install only while the game is closed**

Confirm `TS4_x64` is not running. Push `fix/native-newborn-carry`, run `install_mod.ps1`, and verify PR #7 points to the pushed head. If the game is running, stop before installation and ask the user to close it.
