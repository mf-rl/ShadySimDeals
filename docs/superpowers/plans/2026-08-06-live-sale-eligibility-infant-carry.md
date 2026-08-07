# Live Sale Eligibility and Infant Carry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix wider relationship timing, exclude off-lot Sims from both sale pickers, and make sellers carry infants into household-sale rabbit holes.

**Architecture:** Preserve the existing transaction workflow. Add one shared presence predicate for picker candidates, snapshot wider relationship deltas immediately before target disposition, and prepend EA's native infant pickup or handoff path to only the infant household-member rabbit-hole path.

**Tech Stack:** Python 3.7-compatible Sims 4 scripts, Python 3.12 and pytest, native Sims 4 `SimInfo`, `RelationshipTracker`, `InteractionContext`, and interaction tuning APIs.

## Global Constraints

- Do not change pricing, sale durations, payment ordering, or transaction recovery.
- Do not add dependencies or custom carry tuning.
- Use EA pickup interaction `271032` for uncarried infants and EA handoff continuation `269721` for infants carried by another Sim.
- Do not push changes.

---

### Task 1: Filter both pickers to Sims on the active lot

**Files:**
- Modify: `src/shady_sim_deals/sims4_runtime.py:24-94`
- Test: `tests/test_runtime.py:80-140`
- Test: `tests/test_runtime.py:370-405`

**Interfaces:**
- Consumes: `SimInfo.is_instanced() -> bool` with the native default hidden-instance behavior.
- Produces: `_is_on_active_lot(sim_info) -> bool`, used by both eligibility functions.

- [ ] **Step 1: Extend the test SimInfo with native-shaped presence behavior**

Add an `instanced=True` constructor argument and method to the existing runtime `FakeSimInfo`:

```python
self.instanced = instanced

def is_instanced(self):
    return self.instanced
```

- [ ] **Step 2: Write failing picker tests**

Add one absent household member to the household picker test and one absent pregnant Sim to the unborn picker test:

```python
FakeSimInfo("at_school", age="CHILD", instanced=False)
```

```python
FakeSimInfo("at_work", pregnant=True, instanced=False)
```

Assert neither ID appears while existing on-lot candidates still do.

- [ ] **Step 3: Run the focused tests and verify RED**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_runtime.py -k "eligible_household_member_ids or eligible_unborn_ids"
```

Expected: FAIL because the absent candidates are still returned.

- [ ] **Step 4: Add the shared native presence guard**

Add beside the candidate builders:

```python
def _is_on_active_lot(sim_info):
    try:
        return bool(sim_info.is_instanced())
    except Exception:
        return False
```

Include `_is_on_active_lot(sim_info)` in the `valid` expression created by both `eligible_household_member_ids` and `eligible_unborn_ids`.

- [ ] **Step 5: Run the focused tests and verify GREEN**

Run the command from Step 3. Expected: PASS.

- [ ] **Step 6: Commit the picker fix locally**

```powershell
git add src/shady_sim_deals/sims4_runtime.py tests/test_runtime.py
git commit -m "fix: exclude off-lot sale candidates"
```

---

### Task 2: Snapshot wider relationship consequences before transfer

**Files:**
- Modify: `src/shady_sim_deals/orchestrator.py:70-110`
- Modify: `src/shady_sim_deals/sims4_adapters.py:164-330`
- Test: `tests/test_transactions.py:1-95`
- Test: `tests/test_sims4_adapters.py:330-470`

**Interfaces:**
- Produces: `Sims4SaleConsequences.capture(transaction) -> None`.
- Stores: `transaction.wider_relationship_deltas`, a `dict[str, int]` captured before target processing.
- Consumes: the captured mapping from `Sims4SaleConsequences.apply(transaction)` after successful transfer and payment.

- [ ] **Step 1: Write a failing orchestration-order test**

Use a consequence recorder with `capture` and `apply` methods, then assert capture happens before target processing and apply happens afterward:

```python
class CapturingConsequences(Recorder):
    def capture(self, transaction):
        self.events.append("capture_consequences")

    def apply(self, transaction):
        self.events.append("consequences")


assert events.index("capture_consequences") < events.index("target")
assert events.index("target") < events.index("consequences")
```

- [ ] **Step 2: Write a failing adapter snapshot test**

Create seller, target, mother, and unrelated household Sim fakes. Call `capture(transaction)`, mutate both lookup sources to empty results to represent post-transfer state, then call `apply(transaction)`.

Assert the mother receives `-50`, the unrelated household Sim receives `-25`, and neither seller nor target is included.

- [ ] **Step 3: Run the focused tests and verify RED**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_transactions.py tests/test_sims4_adapters.py -k "capture_consequences or snapshot"
```

Expected: FAIL because `capture` and the pre-disposition hook do not exist.

- [ ] **Step 4: Add the pre-disposition capture hook**

In `_finish_after_rabbit_hole`, after successful revalidation and before `target_disposition_pending`, call the optional hook so existing lightweight consequence doubles remain compatible:

```python
capture_consequences = getattr(self._consequences, "capture", None)
if capture_consequences is not None:
    capture_consequences(transaction)
```

- [ ] **Step 5: Extract and capture the existing wider delta calculation**

Move the current household/genealogy collection from `_apply_wider_relationships` into `_wider_relationship_deltas(transaction)`. Preserve its two independent source-level exception handlers and overlap rule.

Add:

```python
def capture(self, transaction):
    if transaction.transaction_type == "household_member":
        transaction.wider_relationship_deltas = (
            self._wider_relationship_deltas(transaction)
        )
```

Make `_apply_wider_relationships` consume the captured mapping, retaining a calculation fallback for direct adapter callers:

```python
deltas = getattr(transaction, "wider_relationship_deltas", None)
if deltas is None:
    deltas = self._wider_relationship_deltas(transaction)
```

Keep the existing per-Sim tracker update and exception logging unchanged.

- [ ] **Step 6: Run the focused tests and verify GREEN**

Run the command from Step 3. Expected: PASS.

- [ ] **Step 7: Run transaction and consequence regression tests**

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_transactions.py tests/test_sims4_adapters.py
```

Expected: PASS.

- [ ] **Step 8: Commit the relationship fix locally**

```powershell
git add src/shady_sim_deals/orchestrator.py src/shady_sim_deals/sims4_adapters.py tests/test_transactions.py tests/test_sims4_adapters.py
git commit -m "fix: capture relationship audience before transfer"
```

---

### Task 3: Carry infants before starting the shared rabbit hole

**Files:**
- Modify: `src/shady_sim_deals/sims4_adapters.py:398-505`
- Test: `tests/test_sims4_adapters.py:570-850`
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`
- Modify: `DEVELOPMENT.md`
- Modify: `SPECS_CHECKLIST.md`

**Interfaces:**
- Adds constructor dependency: `infant_pickup=None`, a callable `(actor_sim_info, target_sim_info, callback) -> bool`.
- Produces: `_queue_infant_pickup(actor, target, callback) -> bool` using interaction tuning ID `271032`.
- Preserves: `run(transaction, on_finished) -> bool` and the existing final callback contract `on_finished(canceled: bool)`.

- [ ] **Step 1: Write a failing infant sequence test**

Inject a pickup callable that records its callback. Start an infant sale and assert the shared rabbit-hole service has not started. Complete pickup naturally and assert the service starts with `[actor, target]`:

```python
pickup_callbacks = []
adapter = Sims4RabbitHoleAdapter(
    rabbit_hole_service=service,
    sim_info_lookup=lookup,
    rabbit_hole_lookup=lambda instance: instance,
    infant_pickup=lambda actor, target, callback: (
        pickup_callbacks.append(callback) or True
    ),
)

adapter.run(transaction, finished.append)
assert service.started == []
pickup_callbacks[0](canceled=False)
assert service.started == [([actor, target], expected_tuning_id)]
```

- [ ] **Step 2: Write a failing pickup-cancellation test**

Using the same injected pickup seam, invoke `pickup_callbacks[0](canceled=True)`. Assert the shared rabbit hole never starts and the transaction callback receives `True`.

- [ ] **Step 3: Write a failing native pickup wiring test**

Provide fake `services`, `sims4.resources`, `interactions.context`, and `interactions.priority` modules. Return fake instantiated seller/infant Sims and an enqueue result whose interaction records a finishing callback.

Assert `_queue_infant_pickup`:

- resolves interaction tuning ID `271032`;
- calls `seller_sim.push_super_affordance(affordance, infant_sim, context)`;
- reports `canceled=False` only when the pickup interaction finishes naturally.

- [ ] **Step 4: Run the focused tests and verify RED**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_sims4_adapters.py -k "infant and (pickup or rabbit_hole)"
```

Expected: FAIL because the adapter starts the shared rabbit hole immediately and has no pickup seam.

- [ ] **Step 5: Isolate existing rabbit-hole startup**

Move the service call, callback registry, expiration callback, and cleanup currently in `run` into `_start_rabbit_hole(actor, target, rabbit_hole_type, solo, on_finished)`. Do not change that code's behavior.

- [ ] **Step 6: Prepend pickup only for household-sale infants**

Add `INFANT_PICKUP_AFFORDANCE_ID = 271032`. In `run`, after participant and rabbit-hole tuning resolution:

```python
if transaction.transaction_type == "household_member" and age_key(target) == "infant":
    def after_pickup(canceled=False):
        if canceled:
            on_finished(True)
            return
        try:
            self._start_rabbit_hole(
                actor, target, rabbit_hole_type, False, on_finished
            )
        except Exception:
            on_finished(True)

    if not self._infant_pickup(actor, target, after_pickup):
        raise IntegrationUnavailable("Infant pickup could not start")
    return True
```

All other paths call `_start_rabbit_hole` immediately.

- [ ] **Step 7: Implement the native pickup queue**

Resolve both visible instances with `get_sim_instance()`, the interaction affordance from the interaction instance manager, and construct:

```python
InteractionContext(actor_sim, InteractionContext.SOURCE_SCRIPT, Priority.High)
```

Queue it with `actor_sim.push_super_affordance(affordance, target_sim, context)`. Reject a false enqueue result or an already-finishing interaction. Register a finishing callback that passes `not interaction.is_finishing_naturally` to the adapter callback.

- [ ] **Step 8: Run focused and full adapter tests**

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_sims4_adapters.py -k "infant and (pickup or rabbit_hole)"
py -3.12 -m pytest -q -p no:cacheprovider tests/test_sims4_adapters.py
```

Expected: PASS.

- [ ] **Step 9: Align maintained documentation**

Document that both pickers require on-lot Sims, wider audiences are captured before transfer, and infant sales use native pickup before rabbit-hole entry. Add three unchecked live verification entries to `SPECS_CHECKLIST.md` for the reported scenarios.

- [ ] **Step 10: Run final verification**

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests
py -3.12 build_mod.py
git diff --check
git status --short --branch
```

Expected: all tests pass, both mod artifacts build, `git diff --check` is empty, and only intended documentation/code/test changes are present.

- [ ] **Step 11: Commit the infant and documentation fix locally**

```powershell
git add src/shady_sim_deals/sims4_adapters.py tests/test_sims4_adapters.py README.md ARCHITECTURE.md DEVELOPMENT.md SPECS_CHECKLIST.md docs/superpowers/plans/2026-08-06-live-sale-eligibility-infant-carry.md
git commit -m "fix: carry infants into sale rabbit holes"
```

---

### Task 4: Handoff infants already carried by another Sim

**Files:**
- Modify: `src/shady_sim_deals/sims4_adapters.py:470-570`
- Test: `tests/test_sims4_adapters.py:710-840`
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`
- Modify: `DEVELOPMENT.md`
- Modify: `SPECS_CHECKLIST.md`

**Interfaces:**
- Consumes: `target_sim.parent`, where a Sim parent is the current carrier.
- Produces: native handoff continuation `269721` queued by the current carrier with `target=actor_sim` and `carry_target=target_sim`.
- Preserves: `_queue_infant_pickup(actor, target, callback) -> bool` and `callback(canceled: bool)`.

- [ ] **Step 1: Write the failing carried-infant handoff test**

Create seller, mother, and infant Sim instances. Set `infant.parent = mother`, make the mother record `push_super_affordance`, and expose both pickup and handoff affordances from the fake interaction manager.

```python
assert adapter._queue_infant_pickup(actor, infant, callbacks.append)
assert requested_ids == [269721]
assert mother.pushes == [
    (handoff_affordance, actor, context, {"carry_target": infant})
]

infant.parent = actor
finishing_callbacks[0](handoff_interaction)
assert callbacks == [False]
```

- [ ] **Step 2: Write the failing ownership-verification test**

Finish the same handoff naturally without changing `infant.parent` from the mother. Assert the callback receives cancellation and no rabbit hole starts:

```python
finishing_callbacks[0](handoff_interaction)
assert callbacks == [True]
assert service.started == []
```

- [ ] **Step 3: Run the focused tests and verify RED**

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_sims4_adapters.py -k "infant and (handoff or ownership)"
```

Expected: FAIL because `_queue_infant_pickup` always requests `271032` from the seller and does not verify final carry ownership.

- [ ] **Step 4: Select EA's native handoff for a carried infant**

Add `INFANT_HANDOFF_AFFORDANCE_ID = 269721`. In `_queue_infant_pickup`, resolve `target_sim.parent`. When that parent has `is_sim` and is not the seller, queue the handoff from the carrier:

```python
carrier = getattr(target_sim, "parent", None)
if getattr(carrier, "is_sim", False) and carrier is not actor_sim:
    source_sim = carrier
    interaction_target = actor_sim
    affordance_id = self.INFANT_HANDOFF_AFFORDANCE_ID
    interaction_kwargs = {"carry_target": target_sim}
else:
    source_sim = actor_sim
    interaction_target = target_sim
    affordance_id = self.INFANT_PICKUP_AFFORDANCE_ID
    interaction_kwargs = {}
```

Construct the script context for `source_sim` and pass `**interaction_kwargs` to `push_super_affordance`.

- [ ] **Step 5: Gate completion on actual carry ownership**

Change the finishing callback to cancel unless both conditions hold:

```python
completed = (
    interaction.is_finishing_naturally
    and target_sim.parent is actor_sim
)
callback(not completed)
```

Update the existing uncarried-pickup wiring test to set `target.parent = actor` before completing the fake interaction.

- [ ] **Step 6: Run focused and adapter regression tests**

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_sims4_adapters.py -k "infant and (pickup or handoff or ownership or rabbit_hole)"
py -3.12 -m pytest -q -p no:cacheprovider tests/test_sims4_adapters.py
```

Expected: PASS.

- [ ] **Step 7: Align maintained documentation and live checklist**

Document the native carried-infant handoff and ownership gate. Keep the live handoff item unchecked until it passes in game.

- [ ] **Step 8: Run final verification and install the exact build**

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests
py -3.12 build_mod.py
git diff --check
.\install_mod.ps1
Get-FileHash dist\ShadySimDeals.ts4script
Get-FileHash "$env:USERPROFILE\Documents\Electronic Arts\The Sims 4\Mods\ShadySimDeals\ShadySimDeals.ts4script"
```

Expected: all tests pass, artifacts build, whitespace validation is clean, installation succeeds with the game closed, and both script hashes match.

- [ ] **Step 9: Commit locally**

```powershell
git add src/shady_sim_deals/sims4_adapters.py tests/test_sims4_adapters.py README.md ARCHITECTURE.md DEVELOPMENT.md SPECS_CHECKLIST.md docs/superpowers/plans/2026-08-06-live-sale-eligibility-infant-carry.md
git commit -m "fix: hand off carried infants before sale"
```
