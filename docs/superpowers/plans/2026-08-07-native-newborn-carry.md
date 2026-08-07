# Native Newborn Carry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete EA's natural newborn put-down before native `baby_CheckOn_Minor` continues into persistent `baby_HeldActions`, without changing any other sale flow.

**Architecture:** Keep the existing `Sims4RabbitHoleAdapter._queue_infant_pickup` boundary and its separate newborn branch. End an existing carrier's `baby_HeldActions` with `cancel(FinishingType.NATURAL, ...)`, wait for the visible put-down/restore-to-crib exit, and only then queue `baby_CheckOn_Minor` (`275655`). Accept pickup only when its continuation leaves `baby_HeldActions` (`275181`) active on the seller with the newborn as target and the newborn parented to the seller. The infant branch and all downstream rabbit-hole, transfer, pricing, consequence, and payment code remain unchanged.

**Tech Stack:** Python 3.7-compatible Sims 4 script code, pytest under Python 3.12, EA interaction tuning IDs, PowerShell build/install scripts.

## Global Constraints

- Change only the `target_age == "baby"` branch in `Sims4RabbitHoleAdapter._queue_infant_pickup`.
- Keep infant pickup `271032` and handoff `269721` unchanged.
- Do not manually mutate object parenting or newborn state.
- Do not add dependencies, custom animations, or carry implementations.
- Commit reviewed changes and push them to existing PR #7 without collaborator or AI attribution.
- Keep the live newborn checklist pending until the complete sale passes in game.

---

### Task 1: Replace HoldOut with native persistent newborn carry

**Files:**
- Modify: `tests/test_sims4_adapters.py`
- Modify: `src/shady_sim_deals/sims4_adapters.py`
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`
- Modify: `DEVELOPMENT.md`
- Modify: `SPECS_CHECKLIST.md`

**Interfaces:**
- Consumes: `Sims4RabbitHoleAdapter._queue_infant_pickup(actor, target, callback) -> bool`
- Produces: newborn pickup through constants `NEWBORN_CHECK_ON_AFFORDANCE_ID = 275655` and `NEWBORN_HELD_ACTIONS_AFFORDANCE_ID = 275181`; callback receives `False` only after persistent seller carry ownership is verified.

- [x] **Step 1: Replace the HoldOut regression with a failing native-continuation test**

Update `test_carried_newborn_is_released_then_held_by_seller` so the fake CheckOn interaction finishes after adding the persistent interaction to the seller:

```python
held_actions = SimpleNamespace(
    affordance=SimpleNamespace(guid64=275181),
    target=env.carry_target,
)

assert adapter._queue_infant_pickup(
    env.actor, env.infant, callbacks.append
)
env.finishing_callbacks[0](env.interaction)
assert env.requested_ids == [275655]

env.carry_target.parent = env.actor
env.actor.si_state = [held_actions]
check_on_callbacks[0](check_on_interaction)
assert callbacks == [False]
```

Keep `test_native_infant_pickup_queues_ea_affordance`, `test_carried_infant_uses_native_handoff_before_rabbit_hole`, and the parameterized BABY/INFANT seller-only rabbit-hole ordering test unchanged.

- [x] **Step 2: Run the focused test and verify RED**

Run:

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests\test_sims4_adapters.py -k "carried_newborn_is_released_then_held_by_seller or native_infant_pickup or carried_infant"
```

Expected: the newborn test fails because production requests `13011` instead of `275655`; infant tests pass.

- [x] **Step 3: Implement the newborn-only native sequence**

In `Sims4RabbitHoleAdapter`, replace `NEWBORN_HOLD_AFFORDANCE_ID` with:

```python
NEWBORN_CHECK_ON_AFFORDANCE_ID = 275655
NEWBORN_HELD_ACTIONS_AFFORDANCE_ID = 275181
```

In the existing newborn branch, preserve carrier release, but replace `queue_hold` with `queue_check_on`. Push `NEWBORN_CHECK_ON_AFFORDANCE_ID`, then verify its continuation at finish:

```python
held_actions = next(
    (
        active
        for active in getattr(actor_sim, "si_state", ())
        if getattr(
            getattr(active, "affordance", None), "guid64", None
        ) == self.NEWBORN_HELD_ACTIONS_AFFORDANCE_ID
        and getattr(active, "target", None) is target_sim
    ),
    None,
)
completed = (
    interaction.is_finishing_naturally
    and held_actions is not None
    and target_sim.parent is actor_sim
)
callback(not completed)
```

Retain diagnostic logging, renaming `newborn_hold_queued` and `newborn_hold_finished` to `newborn_check_on_queued` and `newborn_check_on_finished`, and include `held_actions_active=held_actions is not None` in the finish event.

- [x] **Step 4: Run focused tests and verify GREEN**

Run the Step 2 command. Expected: all selected newborn and infant tests pass.

- [x] **Step 5: Align current-state documentation**

- `README.md`, `ARCHITECTURE.md`, and `DEVELOPMENT.md`: replace Hold `13011` with CheckOn `275655` continuing into HeldActions `275181`.
- `SPECS_CHECKLIST.md`: retain the unchecked live item and state that the corrected native continuation awaits live validation.
- Do not rewrite historical design or plan documents.

- [x] **Step 6: Verify all existing functionality**

Run:

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests
py -3.12 build_mod.py
git diff --check
```

Expected: the complete suite passes, both mod artifacts build, and `git diff --check` exits zero.

- [x] **Step 7: Review scope and install**

Run `git diff -- src/shady_sim_deals/sims4_adapters.py tests/test_sims4_adapters.py README.md ARCHITECTURE.md DEVELOPMENT.md SPECS_CHECKLIST.md` and confirm no non-newborn production path changed. When The Sims 4 is closed, run:

```powershell
.\install_mod.ps1
```

Expected: the installer copies the verified artifacts to the game Mods directory. This historical task was completed before PR #7 was selected as the integration path.

---

### Task 2: Replace user cancellation with natural newborn put-down

**Files:**
- Modify: `tests/test_sims4_adapters.py`
- Modify: `src/shady_sim_deals/sims4_adapters.py`
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`
- Modify: `DEVELOPMENT.md`
- Modify: `SPECS_CHECKLIST.md`

**Interfaces:**
- Consumes: the existing newborn-only `queue_check_on` callback and `baby_HeldActions` interaction selected by target identity.
- Produces: a carrier release through `interaction.cancel(FinishingType.NATURAL, cancel_reason_msg=...)`; Check On starts only after the carrier finishes naturally and no longer parents the newborn.

- [x] **Step 1: Write failing natural-release regressions**

Update `test_carried_newborn_is_released_then_held_by_seller` to expose a fake `FinishingType.NATURAL`, record calls to `interaction.cancel`, and assert:

```python
assert release_requests == [
    ("natural", {"cancel_reason_msg": "Shady Sim Deals newborn handoff"})
]
assert env.requested_ids == []

env.carry_target.parent = None
env.finishing_callbacks[0](env.interaction)
assert env.requested_ids == [275655]
```

Replace `test_rejected_newborn_release_unregisters_finishing_callback` with `test_newborn_natural_release_exception_unregisters_finishing_callback`, where `interaction.cancel` raises `RuntimeError`; require `_queue_infant_pickup` to return `False` and leave no finishing callback registered.

Add `test_unnatural_newborn_release_cancels_without_check_on`: invoke the carrier finishing callback with `is_finishing_naturally=False` and require `callbacks == [True]` and `requested_ids == []`.

- [x] **Step 2: Run focused tests and verify RED**

Run:

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests\test_sims4_adapters.py -k "carried_newborn_is_released or natural_release_exception or unnatural_newborn_release or native_infant_pickup or carried_infant"
```

Expected: newborn natural-release tests fail because production still calls `cancel_user`; infant controls pass.

- [x] **Step 3: Implement natural carrier completion**

Import `FinishingType` inside `_queue_infant_pickup`:

```python
from interactions.interaction_finisher import FinishingType
```

Replace the carrier's direct `queue_check_on` finishing callback with:

```python
def carrier_finished(interaction):
    if (
        not interaction.is_finishing_naturally
        or target_sim.parent is carrier
    ):
        callback(True)
        return
    queue_check_on()
```

Register `carrier_finished`, request the natural finish, and clean up only if that request raises:

```python
held_interaction.register_on_finishing_callback(carrier_finished)
try:
    held_interaction.cancel(
        FinishingType.NATURAL,
        cancel_reason_msg="Shady Sim Deals newborn handoff",
    )
except Exception:
    held_interaction.unregister_on_finishing_callback(carrier_finished)
    return failed("carrier_release_exception")
return True
```

Do not call `cancel_user()` and do not manually mutate newborn parenting or state.

- [x] **Step 4: Run focused tests and verify GREEN**

Run the Step 2 command. Expected: all selected newborn and infant tests pass.

- [x] **Step 5: Align current-state documentation**

- `README.md`, `ARCHITECTURE.md`, and `DEVELOPMENT.md`: state that the previous carrier completes a natural visible put-down before seller Check On.
- `SPECS_CHECKLIST.md`: keep live newborn sale unchecked and state that natural put-down awaits validation.

- [ ] **Step 6: Verify, review, commit, and update PR #7**

Run:

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests
py -3.12 build_mod.py
git diff --check
```

Request read-only review over `bb78c4821c24faaf544557b0a120c817170bae4a..HEAD` plus the working-tree change. Fix all Critical and Important findings. Commit with conventional commit subject `fix: finish newborn release naturally`, push `fix/native-newborn-carry`, and install after The Sims 4 is closed.
