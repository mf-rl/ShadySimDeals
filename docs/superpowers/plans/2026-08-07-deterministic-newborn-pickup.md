# Deterministic Newborn Pickup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace random newborn Check On selection with one private interaction that deterministically enters EA Cuddle under persistent Held Actions before the existing sale rabbit hole.

**Architecture:** Package an invisible script-only `SuperInteraction` whose only outcome continues to EA Cuddle (`275239`) with `baby_HeldActions` (`275181`) as its SI override. Keep the existing carrier-exit and seller SI-state watchers, reservation, ownership verification, rabbit hole, transfer, and payment; change only the newborn interaction resource and treat targeted Held Actions plus seller parenting as the authoritative success signal.

**Tech Stack:** Sims 4 XML interaction tuning, DBPF package resources, Python 3.7-compatible game script, pytest under Python 3.12, PowerShell build/install scripts.

## Global Constraints

- Add private interaction instance `0xEAA21FFB1081E025` with resource type `0xE882D22F` and group `0`.
- Use EA Cuddle `275239` as the single continuation and EA Held Actions `275181` as `si_affordance_override`.
- Do not override or inject into EA Check On, Cuddle, Held Actions, any pie menu, or autonomy.
- Do not add custom animation, manual parenting, routing override, dependency, retry, or polling.
- Preserve the caregiver's natural put-down and both existing SI-state watcher boundaries.
- Accept pickup only when seller Held Actions targets the newborn and the newborn parent is the seller; do not require `is_finishing_naturally` after ownership is proven.
- Preserve infant behavior and all downstream rabbit-hole, transfer, consequence, and payment behavior.
- Keep live completion pending until the full carried-newborn sale passes in game.
- Commit and push reviewed changes to existing PR #7 without collaborator or AI attribution.

---

### Task 1: Package the private deterministic pickup interaction

**Files:**
- Create: `tuning/interactions/newborn_pickup.xml`
- Modify: `build_mod.py:402-642`
- Modify: `tests/test_build.py:7-55`
- Modify: `tests/test_build.py` near packaged-interaction tests
- Modify: `docs/superpowers/plans/2026-08-07-deterministic-newborn-pickup.md`

**Interfaces:**
- Consumes: EA interaction tuning IDs Cuddle `275239` and Held Actions `275181`.
- Produces: packaged interaction resource `(0xE882D22F, 0, 0xEAA21FFB1081E025)` retrievable from the game interaction instance manager.

- [x] **Step 1: Add the expected package key and deterministic tuning test**

Add this key to `EXPECTED_RESOURCE_KEYS`:

```python
(0xE882D22F, 0, 0xEAA21FFB1081E025),
```

Add the behavior test:

```python
def test_newborn_pickup_has_one_native_held_cuddle_continuation():
    pickup = packaged_interactions()[0xEAA21FFB1081E025]

    assert pickup.attrib == {
        "c": "SuperInteraction",
        "i": "interaction",
        "m": "interactions.base.super_interaction",
        "n": "ShadySimDeals:NewbornPickup",
        "s": str(0xEAA21FFB1081E025),
    }
    assert pickup.find("./T[@n='allow_autonomous']").text == "False"
    assert pickup.find("./T[@n='allow_user_directed']").text == "False"
    assert pickup.find("./T[@n='visible']").text == "False"

    continuations = pickup.findall(".//L[@n='continuation']/U")
    assert len(continuations) == 1
    assert continuations[0].find("./T[@n='affordance']").text == "275239"
    assert (
        continuations[0].find("./T[@n='si_affordance_override']").text
        == "275181"
    )
```

This catches a missing resource, accidental visibility/injection, multiple
weighted outcomes, the wrong native action, or a missing persistent SI override.

- [x] **Step 2: Run the package tests and verify RED**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests\test_build.py -k "newborn_pickup or package_resources_include_every_planned_resource"
```

Expected: failures report missing key `0xEAA21FFB1081E025` and absent packaged
interaction.

- [x] **Step 3: Create the private tuning XML**

Create `tuning/interactions/newborn_pickup.xml` with this complete content:

```xml
<?xml version="1.0" encoding="utf-8"?>
<I c="SuperInteraction" i="interaction" m="interactions.base.super_interaction" n="ShadySimDeals:NewbornPickup" s="16907111114276462629">
  <L n="_constraints"><U><L n="constraints"><U><V n="value" t="posture"><U n="posture"><L n="posture_manifest_tuning">
    <U><V n="posture_type" t="enabled"><T n="enabled">15537</T></V></U>
    <U><V n="posture_type" t="enabled"><T n="enabled">30530</T></V></U>
    <U><V n="posture_type" t="enabled"><T n="enabled">23832</T></V></U>
    <U><V n="posture_type" t="enabled"><T n="enabled">15535</T></V></U>
  </L></U></V></U></L></U></L>
  <V n="_saveable" t="disabled" />
  <T n="allow_autonomous">False</T>
  <T n="allow_user_directed">False</T>
  <V n="basic_content" t="one_shot" />
  <V n="canonical_animation" t="disabled" />
  <V n="outcome" t="test_based"><U n="test_based">
    <L n="fallback_outcomes"><U>
      <U n="outcome"><L n="continuation"><U>
        <T n="affordance">275239</T>
        <T n="si_affordance_override">275181</T>
      </U></L></U>
      <U n="weight"><T n="base_value">1</T></U>
    </U></L>
    <T n="use_fallback_as_default">True</T>
  </U></V>
  <E n="target_type">OBJECT</E>
  <T n="visible">False</T>
</I>
```

The decimal instance value is exactly `0xEAA21FFB1081E025`. The four posture
types are copied from patch `1.125.59.1030` `baby_CheckOn_Minor`; the outcome
removes all random need-selection branches.

- [x] **Step 4: Add the tuning to `package_resources()`**

Add this tuple beside the existing interaction tuning resources:

```python
(
    (ROOT / "tuning" / "interactions" / "newborn_pickup.xml").read_bytes(),
    INTERACTION_TUNING_TYPE,
    0,
    0xEAA21FFB1081E025,
),
```

Do not add it to Lot51 injectors, categories, phone/computer affordances, or icon
resources.

- [x] **Step 5: Run focused and complete build tests**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests\test_build.py -k "newborn_pickup or package_resources_include_every_planned_resource"
py -3.12 -m pytest -q -p no:cacheprovider tests\test_build.py
```

Expected: focused resource/tuning tests pass, then all build tests pass.

- [x] **Step 6: Commit the packaged interaction**

```powershell
git add tuning/interactions/newborn_pickup.xml build_mod.py tests/test_build.py docs/superpowers/plans/2026-08-07-deterministic-newborn-pickup.md
git commit -m "feat: package deterministic newborn pickup"
```

---

### Task 2: Use deterministic pickup and authoritative carry ownership

**Files:**
- Modify: `src/shady_sim_deals/sims4_adapters.py:408-915`
- Modify: `tests/test_sims4_adapters.py:830-1760`
- Modify: `docs/superpowers/plans/2026-08-07-deterministic-newborn-pickup.md`

**Interfaces:**
- Consumes: private interaction `0xEAA21FFB1081E025` packaged by Task 1.
- Produces: unchanged `_queue_infant_pickup(actor, target, callback) -> bool`; callback receives `False` only after targeted seller Held Actions and seller parenting are observed.

- [ ] **Step 1: Change the newborn fixture to expose only the private pickup**

Replace the fixture's Check On mapping with:

```python
newborn_pickup_affordance = object()
affordances = {
    271032: pickup_affordance,
    269721: handoff_affordance,
    0xEAA21FFB1081E025: newborn_pickup_affordance,
}
```

Expose `newborn_pickup_affordance` in the returned environment. Rename local
`check_on_interaction` variables in newborn tests to `newborn_pickup_interaction`
so the tests describe the new contract; leave infant fixture names unchanged.

- [ ] **Step 2: Write the private-ID and falsey-completion regressions**

In `test_carried_newborn_is_released_then_held_by_seller`, require:

```python
assert env.requested_ids == [0xEAA21FFB1081E025]
assert env.actor.pushes[0][0:2] == (
    env.newborn_pickup_affordance,
    env.carry_target,
)
```

Set the completed private interaction metadata to the exact shape observed live:

```python
newborn_pickup_interaction.is_finishing_naturally = []
env.carry_target.parent = env.actor
env.actor.si_state.set_interactions(
    SimpleNamespace(
        affordance=SimpleNamespace(guid64=275181),
        target=env.carry_target,
    )
)
env.scheduled_elements[1][1]()

assert callbacks == [False]
```

Keep the existing missing-Held-Actions and wrong-target-Held-Actions tests
expecting `[True]`. They prove the change trusts ownership, not mere interaction
exit.

- [ ] **Step 3: Run the focused adapter test and verify RED**

Run:

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests\test_sims4_adapters.py -k "carried_newborn_is_released or newborn_check_on_without_held_actions or wrong_held_target"
```

Expected: the main test fails because production requests `275655` and rejects
the falsey natural-finishing value even though carry ownership is verified.

- [ ] **Step 4: Switch the newborn-only interaction constant and request**

Replace the Check On constant with:

```python
NEWBORN_PICKUP_AFFORDANCE_ID = 0xEAA21FFB1081E025
```

Rename newborn-local functions and events without changing their control flow:

```python
queue_newborn_pickup
settle_newborn_pickup
newborn_pickup_queued
newborn_pickup_settled
newborn_pickup_startup_exception
newborn_pickup_setup_exception
newborn_pickup_settlement_exception
newborn_pickup_settlement_schedule_exception
newborn_pickup_watcher_removal_exception
```

Request `self.NEWBORN_PICKUP_AFFORDANCE_ID` from the interaction instance
manager. Keep seller watcher registration before the push and exact interaction
identity removal detection unchanged.

- [ ] **Step 5: Make carry ownership the settlement success condition**

Keep `is_finishing_naturally` in the diagnostic log, but remove it from the
decision:

```python
parent = getattr(target_sim, "parent", None)
held_actions = find_held_actions()
succeeded = held_actions is not None and parent is actor_sim

self._logger.log(
    "newborn_pickup_settled",
    finishing_naturally=newborn_pickup_interaction.is_finishing_naturally,
    held_actions_active=held_actions is not None,
    parent_id=(
        str(parent.sim_id)
        if getattr(parent, "sim_id", None) is not None
        else None
    ),
    parent_is_actor=parent is actor_sim,
    target_id=str(target.sim_id),
)
finish(not succeeded)
```

`find_held_actions()` already requires affordance `275181` and exact target
identity, so no additional state or helper is needed.

- [ ] **Step 6: Run focused controls and the full suite**

Run:

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests\test_sims4_adapters.py -k "newborn or native_infant_pickup or carried_infant"
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider
```

Expected: all newborn and infant controls pass, then the complete suite passes.

- [ ] **Step 7: Commit the adapter switch**

```powershell
git add src/shady_sim_deals/sims4_adapters.py tests/test_sims4_adapters.py docs/superpowers/plans/2026-08-07-deterministic-newborn-pickup.md
git commit -m "fix: use deterministic newborn pickup"
```

---

### Task 3: Align documentation, review, package, and install

**Files:**
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`
- Modify: `DEVELOPMENT.md`
- Modify: `SPECS_CHECKLIST.md`
- Modify: `docs/superpowers/plans/2026-08-07-deterministic-newborn-pickup.md`

- [ ] **Step 1: Align maintained documentation with the implementation**

Update the newborn lifecycle descriptions to state that the private invisible
interaction deterministically enters native Cuddle under Held Actions, while the
existing watchers and ownership verification remain. Replace the pending live
checklist detail with:

```markdown
- [ ] Live: newborn appears and can be selected; the latest event-driven Check On attempt reached settlement but selected a valid non-carry care outcome, so no Held Actions or seller parenting appeared (private deterministic native Cuddle pickup awaits validation)
```

Add an automated checklist item for the packaged single Cuddle/Held Actions
continuation. Do not mark live newborn sale complete.

- [ ] **Step 2: Build and inspect the package**

Run:

```powershell
py -3.12 build_mod.py
tar -tf dist\ShadySimDeals.ts4script
```

Expected: build succeeds; script archive contains updated
`shady_sim_deals/sims4_adapters.pyc`; package tests already prove interaction
resource `0xEAA21FFB1081E025` is present exactly once.

- [ ] **Step 3: Review and verify the complete PR range**

Run:

```powershell
git diff --check bb78c4821c24faaf544557b0a120c817170bae4a
git diff --stat bb78c4821c24faaf544557b0a120c817170bae4a
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider
git status --short
```

Use `superpowers:requesting-code-review` for base
`bb78c4821c24faaf544557b0a120c817170bae4a` through HEAD plus working-tree docs.
Resolve every Critical or Important finding and rerun the affected tests, full
suite, build, and diff check. Do not add collaborator or AI attribution.

- [ ] **Step 4: Commit docs, push PR #7, and verify remote tip**

```powershell
git add README.md ARCHITECTURE.md DEVELOPMENT.md SPECS_CHECKLIST.md docs/superpowers/plans/2026-08-07-deterministic-newborn-pickup.md
git commit -m "docs: record deterministic newborn pickup"
git push
gh pr checks 7
git rev-parse HEAD
git rev-parse origin/fix/native-newborn-carry
git status --short
```

Expected: local and remote SHAs match, the worktree is clean, and GitHub either
reports configured checks or explicitly reports none.

- [ ] **Step 5: Install only while the game is closed**

Confirm `TS4_x64.exe` is absent, then run:

```powershell
.\install_mod.ps1
```

Request the live acceptance test from the design spec: caregiver puts the
newborn down, seller enters the lot and performs native Cuddle/pickup, seller
remains carrying the newborn into the rabbit hole, only seller returns, newborn
leaves household and lot, and payment occurs once. Request the latest
`shady_sim_deals.log` on failure.

---

## Plan Self-Review

- Task 1 packages and structurally verifies the exact private interaction from
  the approved design without pie-menu or autonomy injection.
- Task 2 changes only the newborn interaction request and success signal; both
  existing SI-state boundaries, reservation cleanup, and infant path remain.
- The falsey completion regression reproduces the newest live metadata while
  requiring real targeted Held Actions and seller parenting.
- Missing and wrong-target Held Actions remain cancellation cases.
- Task 3 keeps live status pending, reviews the entire user-required PR range,
  rebuilds, pushes, and installs only with the game closed.
- No new runtime abstraction, dependency, retry, polling, custom animation,
  manual parenting, or unrelated refactor is included.
