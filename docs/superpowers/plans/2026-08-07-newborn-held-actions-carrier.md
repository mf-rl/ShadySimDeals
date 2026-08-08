# Newborn Held Actions Carrier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let newborn sales recover the real caregiver from EA's active Held Actions reservation when the Baby object's `parent` is empty.

**Architecture:** Extend only the newborn branch of `Sims4RabbitHoleAdapter._queue_infant_pickup`. Prefer the existing `parent` carrier, otherwise read the newborn's reservation handlers for a foreign Sim's exact Held Actions interaction, then reuse the existing natural-finish, next-tick reservation, and Check On flow unchanged.

**Tech Stack:** Python 3.7-compatible Sims 4 script code, EA object reservation APIs, pytest on Python 3.12, PowerShell build/install scripts.

## Global Constraints

- Preserve infant, toddler-through-elder, unborn, and already seller-held newborn behavior.
- Do not disable autonomy, clobber or force-release reservations, mutate newborn parenting manually, or add custom carry behavior.
- Ignore malformed, unrelated, and seller-owned reservation handlers during foreign-carrier recovery.
- Keep pricing, transfer, consequences, payment, and rabbit-hole duration unchanged.
- Every production behavior change must first have a failing regression test.
- Keep the live newborn checklist pending until the seller carries the newborn into the rabbit hole and the complete sale passes in game.

---

### Task 1: Recover a missing newborn carrier from Held Actions

**Files:**
- Modify: `tests/test_sims4_adapters.py:830-1135`
- Modify: `src/shady_sim_deals/sims4_adapters.py:548-824`

**Interfaces:**
- Consumes: `target_sim.get_reservation_handlers()`, each handler's `sim` and `reservation_interaction`, and Held Actions affordance ID `275181`.
- Produces: unchanged `Sims4RabbitHoleAdapter._queue_infant_pickup(actor, target, callback) -> bool`; a parentless newborn with a foreign Held Actions owner enters the existing carried-newborn release flow.

- [x] **Step 1: Write the missing-parent regression**

Add this test beside `test_carried_newborn_is_released_then_held_by_seller`:

```python
def test_parentless_newborn_uses_foreign_held_actions_reservation(monkeypatch):
    env = carried_infant_handoff_environment(monkeypatch, "BABY")
    env.carry_target.parent = None
    release_requests = []
    env.interaction.target = env.carry_target
    env.interaction.affordance = SimpleNamespace(guid64=275181)
    env.interaction.cancel = lambda finishing_type, **kwargs: (
        release_requests.append((finishing_type, kwargs))
    )
    env.mother.si_state = [env.interaction]
    foreign_handler = SimpleNamespace(
        sim=env.mother,
        reservation_interaction=env.interaction,
    )
    env.carry_target.get_reservation_handlers = lambda: (foreign_handler,)
    callbacks = []
    adapter = sims4_adapters.Sims4RabbitHoleAdapter()

    assert adapter._queue_infant_pickup(
        env.actor, env.infant, callbacks.append
    )
    assert release_requests == [
        (
            "natural",
            {"cancel_reason_msg": "Shady Sim Deals newborn handoff"},
        )
    ]
    assert env.reservation_events == []
    assert env.requested_ids == []

    env.finishing_callbacks[0](env.interaction)
    assert len(env.scheduled_elements) == 1
    sleep, continue_handoff = env.scheduled_elements[0]
    assert sleep is env.next_tick

    continue_handoff()
    assert env.reservation_events[:2] == [
        ("created", env.actor, env.carry_target),
        ("begun", env.actor, env.carry_target),
    ]
    assert env.requested_ids == [275655]
    assert callbacks == []
```

- [x] **Step 2: Run the regression and verify RED**

Run:

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests\test_sims4_adapters.py::test_parentless_newborn_uses_foreign_held_actions_reservation
```

Expected: FAIL because the parentless path immediately attempts the seller reservation instead of naturally finishing the foreign Held Actions interaction.

- [x] **Step 3: Implement the reservation-owner fallback**

Inside the newborn branch, add a local lookup and use it only when `carrier` is not a Sim:

```python
def find_foreign_held_actions_reservation():
    try:
        handlers = target_sim.get_reservation_handlers()
    except Exception:
        return None, None
    for handler in handlers:
        interaction = getattr(handler, "reservation_interaction", None)
        affordance = getattr(interaction, "affordance", None)
        owner = getattr(handler, "sim", None)
        if (
            getattr(affordance, "guid64", None)
            == self.NEWBORN_HELD_ACTIONS_AFFORDANCE_ID
            and owner is not actor_sim
            and getattr(owner, "is_sim", False)
        ):
            return owner, interaction
    return None, None

held_interaction = None
if not getattr(carrier, "is_sim", False):
    carrier, held_interaction = (
        find_foreign_held_actions_reservation()
    )
```

In the existing foreign-carrier branch, scan `carrier.si_state` only when `held_interaction is None`. Keep the existing `carrier_finished`, natural cancellation, next-tick scheduling, seller reservation, and Check On code unchanged.

- [x] **Step 4: Add the unrelated-reservation control**

Add this control beside the missing-parent regression:

```python
def test_parentless_newborn_ignores_unrelated_reservation(monkeypatch):
    env = carried_infant_handoff_environment(monkeypatch, "BABY")
    env.carry_target.parent = None
    release_requests = []
    unrelated_interaction = SimpleNamespace(
        affordance=SimpleNamespace(guid64=12345),
        cancel=lambda *args, **kwargs: release_requests.append((args, kwargs)),
    )
    env.carry_target.get_reservation_handlers = lambda: (
        SimpleNamespace(
            sim=env.mother,
            reservation_interaction=unrelated_interaction,
        ),
    )
    callbacks = []
    adapter = sims4_adapters.Sims4RabbitHoleAdapter()

    assert adapter._queue_infant_pickup(
        env.actor, env.infant, callbacks.append
    )
    assert release_requests == []
    assert env.requested_ids == [275655]
    assert callbacks == []
```

This proves the fallback does not disturb unrelated EA reservations.

- [x] **Step 5: Run focused newborn and infant tests and verify GREEN**

Run:

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests\test_sims4_adapters.py -k "newborn or infant_pickup or carried_infant"
```

Expected: all selected tests pass, including the new parentless fallback, unrelated-reservation control, seller-held newborn controls, and unchanged infant handoff tests.

- [x] **Step 6: Commit the independently verified fix**

```powershell
git add tests/test_sims4_adapters.py src/shady_sim_deals/sims4_adapters.py
git commit -m "fix: recover newborn held actions carrier"
```

---

### Task 2: Align the checklist, verify, review, push, and install

**Files:**
- Modify: `SPECS_CHECKLIST.md:103-112`
- Modify: `docs/superpowers/plans/2026-08-07-newborn-held-actions-carrier.md`

**Interfaces:**
- Consumes: the verified adapter behavior from Task 1 and the latest live diagnostic result.
- Produces: documentation matching the implementation, a reviewed branch, built mod artifacts, and an installed test build while the game is closed.

- [x] **Step 1: Record the implementation without claiming a live pass**

Replace the current newborn live detail with:

```markdown
- [ ] Live: newborn appears and can be selected; the latest attempt found `parent=None` while another Sim still owned Held Actions (`275181`), so the seller reservation was rejected before Check On (Held Actions carrier recovery awaits validation)
```

Add this automated line beside the newborn handoff checks:

```markdown
- [x] Automated: when a newborn has no `parent`, a foreign Held Actions (`275181`) reservation identifies the carrier; its exact interaction finishes naturally before the existing next-tick seller reservation and Check On flow
```

- [x] **Step 2: Run full verification**

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

Expected: all tests pass, `dist/ShadySimDeals.ts4script` and `dist/ShadySimDeals.package` build, and `git diff --check` is silent.

- [x] **Step 3: Request read-only review**

Review the branch diff from `bb78c4821c24faaf544557b0a120c817170bae4a` through `HEAD` plus the working tree. Fix every Critical or Important finding and rerun affected tests.

- [x] **Step 4: Mark this plan complete and commit documentation**

Mark completed checkboxes in this plan, then run:

```powershell
git add SPECS_CHECKLIST.md docs/superpowers/plans/2026-08-07-newborn-held-actions-carrier.md
git commit -m "docs: record held actions carrier recovery"
```

- [ ] **Step 5: Push and install only while the game is closed**

Confirm `TS4_x64` is not running. Push `fix/native-newborn-carry`, run `install_mod.ps1`, and verify PR #7 points to the pushed head. If the game is running, stop before installation and ask the user to close it.
