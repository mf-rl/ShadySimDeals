# Native Newborn Carry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the newborn-only `baby_HoldOut` attempt with EA's native `baby_CheckOn_Minor` continuation into persistent `baby_HeldActions` without changing any other sale flow.

**Architecture:** Keep the existing `Sims4RabbitHoleAdapter._queue_infant_pickup` boundary and its separate newborn branch. After an existing carrier releases the `Baby` object, queue `baby_CheckOn_Minor` (`275655`); accept pickup only when its continuation leaves `baby_HeldActions` (`275181`) active on the seller with the newborn as target and the newborn parented to the seller. The infant branch and all downstream rabbit-hole, transfer, pricing, consequence, and payment code remain unchanged.

**Tech Stack:** Python 3.7-compatible Sims 4 script code, pytest under Python 3.12, EA interaction tuning IDs, PowerShell build/install scripts.

## Global Constraints

- Change only the `target_age == "baby"` branch in `Sims4RabbitHoleAdapter._queue_infant_pickup`.
- Keep infant pickup `271032` and handoff `269721` unchanged.
- Do not manually mutate object parenting or newborn state.
- Do not add dependencies, custom animations, or carry implementations.
- Do not commit or push in this session.
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

Expected: the installer copies the verified artifacts to the game Mods directory. Do not commit or push.
