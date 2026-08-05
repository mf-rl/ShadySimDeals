# Sale Rabbit-Hole Ordering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run household-member and unborn-Nooboo mutations only after their required rabbit holes expire naturally.

**Architecture:** Keep `TransactionOrchestrator` as the single mutation-ordering boundary. Extend `Sims4RabbitHoleAdapter` to select household or unborn private tuning, start one participant for a self-target unborn sale or two participants otherwise, and invoke the existing completion callback only on expiration. Runtime notifications remain callback-driven.

**Tech Stack:** Python 3.7-compatible Sims 4 scripts, Python 3.12 with pytest, Sims 4 XML tuning, DBPF packaging, Lot51 Core 1.43+

## Global Constraints

- Support The Sims 4 patch `1.125.59.1030`.
- Game-side Python must remain compatible with Python 3.7.
- Lot51 Core 1.43 or newer remains the only mod dependency.
- Household sale transfer and payment occur only after natural expiration.
- Unborn pregnancy conclusion and payment occur only after natural expiration.
- A self-target unborn sale sends the selected actor through one rabbit hole once.
- An other-target unborn sale sends actor first and pregnant Sim second; both return.
- Cancellation or startup failure changes no household membership, pregnancy, sold marker, or funds.
- Do not inject private rabbit-hole affordances into phones, computers, or objects.

---

### Task 1: Make the Sims rabbit-hole adapter transaction-aware

**Files:**
- Modify: `tests/test_sims4_adapters.py`
- Modify: `src/shady_sim_deals/sims4_adapters.py`

**Interfaces:**
- Consumes: `Sims4PregnancyAdapter.expected_offspring_count(sim_id) -> int`.
- Produces: `Sims4RabbitHoleAdapter(..., expected_offspring_lookup=None)`.
- Produces: `Sims4RabbitHoleAdapter.run(transaction, on_finished) -> bool` for household, one-Sim unborn, and two-Sim unborn transactions.

- [ ] **Step 1: Extend the fake service and write failing participant-selection tests**

Add `managed` recording to `FakeRabbitHoleService`:

```python
def put_sim_in_managed_rabbithole(self, sim_info, rabbit_hole_type):
    self.managed.append((sim_info, rabbit_hole_type))
    return self.rabbit_hole_id
```

Add tests proving a self-target unborn sale starts exactly one managed rabbit hole and an other-target sale starts one shared rabbit hole:

```python
def test_unborn_rabbit_hole_uses_one_participant_for_pregnant_actor():
    actor = FakeSimInfo("ADULT", sim_id="1")
    service = FakeRabbitHoleService()
    adapter = sims4_adapters.Sims4RabbitHoleAdapter(
        rabbit_hole_service=service,
        sim_info_lookup={"1": actor}.get,
        rabbit_hole_lookup=lambda instance: instance,
        expected_offspring_lookup=lambda sim_id: 1,
    )
    deal = SaleTransaction("unborn", "1", "1", "home")

    assert adapter.run(deal, lambda canceled: None) is True
    assert service.managed == [(actor, 0xEAA21FFB1081E00B)]
    assert service.started == []


def test_unborn_rabbit_hole_uses_actor_then_pregnant_target():
    actor = FakeSimInfo("ADULT", sim_id="1")
    target = FakeSimInfo("ADULT", sim_id="2")
    service = FakeRabbitHoleService()
    adapter = sims4_adapters.Sims4RabbitHoleAdapter(
        rabbit_hole_service=service,
        sim_info_lookup={"1": actor, "2": target}.get,
        rabbit_hole_lookup=lambda instance: instance,
        expected_offspring_lookup=lambda sim_id: 1,
    )
    deal = SaleTransaction("unborn", "1", "2", "home")

    assert adapter.run(deal, lambda canceled: None) is True
    assert service.started == [([actor, target], 0xEAA21FFB1081E00C)]
    assert service.managed == []
```

- [ ] **Step 2: Write failing duration-selection tests**

```python
@pytest.mark.parametrize(
    ("count", "solo_id", "shared_id"),
    (
        (1, 0xEAA21FFB1081E00B, 0xEAA21FFB1081E00C),
        (2, 0xEAA21FFB1081E00D, 0xEAA21FFB1081E00E),
        (3, 0xEAA21FFB1081E00F, 0xEAA21FFB1081E010),
        (4, 0xEAA21FFB1081E00F, 0xEAA21FFB1081E010),
    ),
)
def test_unborn_rabbit_hole_selects_offspring_duration(count, solo_id, shared_id):
    # Construct self-target and other-target transactions as above and assert
    # their recorded tuning IDs equal solo_id and shared_id.
```

Replace the comment body with the same explicit fake construction used in Step 1 before committing the test.

- [ ] **Step 3: Run adapter tests and verify RED**

Run:

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_sims4_adapters.py -k "unborn_rabbit_hole"
```

Expected: FAIL because the constructor lacks `expected_offspring_lookup`, the fake lacks managed startup state, and all transactions use the household age mapping.

- [ ] **Step 4: Implement the minimum transaction-aware selection**

Add these maps and constructor seam:

```python
UNBORN_SOLO_BY_COUNT = {
    1: 0xEAA21FFB1081E00B,
    2: 0xEAA21FFB1081E00D,
    3: 0xEAA21FFB1081E00F,
}
UNBORN_SHARED_BY_COUNT = {
    1: 0xEAA21FFB1081E00C,
    2: 0xEAA21FFB1081E00E,
    3: 0xEAA21FFB1081E010,
}
```

Store `expected_offspring_lookup`. In `run`, branch on `transaction.transaction_type`. For unborn, clamp the count with `min(3, max(1, int(...)))`; use `put_sim_in_managed_rabbithole(actor, rabbit_hole_type)` when actor and target IDs match, otherwise use the existing shared call with `[actor, target]`. Keep callback registration on the actor and preserve callback-registration rollback.

- [ ] **Step 5: Run adapter and transaction tests**

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_sims4_adapters.py tests/test_transactions.py
```

Expected: PASS.

- [ ] **Step 6: Commit the adapter behavior**

```powershell
git add src/shady_sim_deals/sims4_adapters.py tests/test_sims4_adapters.py
git commit -m "feat: route unborn sales through rabbit holes"
```

---

### Task 2: Delay unborn mutation and notifications until expiration

**Files:**
- Modify: `tests/test_runtime.py`
- Modify: `src/shady_sim_deals/sims4_runtime.py`

**Interfaces:**
- Extends: `complete_unborn_sale(..., on_finished=None) -> SaleTransaction`.
- Produces: `_UnbornSaleInteraction._on_sale_finished(transaction, target_id)`.
- Consumes: the transaction-aware `Sims4RabbitHoleAdapter` from Task 1.

- [ ] **Step 1: Write a failing delayed unborn transaction test**

```python
def test_unborn_sale_waits_for_rabbit_hole_before_pregnancy_and_payment():
    events = []
    rabbit_hole = DelayedRabbitHole(events)
    target = RuntimeRecorder(events)
    target.requires_prepayment = True
    workflow = TransactionOrchestrator(
        RuntimeRecorder(events), RuntimeRecorder(events), rabbit_hole,
        target, RuntimeRecorder(events), RuntimeRecorder(events),
    )
    pregnancy = FakePregnancies(("pregnant",))

    deal = sims4_runtime.complete_unborn_sale(
        "actor", "pregnant", "home",
        lambda sim_id: FakeSimInfo("pregnant"),
        pregnancy, workflow, SimSalePricingService(),
    )

    assert deal.state == "rabbit_hole_started"
    assert "target" not in events
    assert not any(isinstance(event, tuple) and event[0] == "payment" for event in events)

    rabbit_hole.callback(canceled=False)

    assert deal.state == "completed"
    assert events.index(("payment", "home", 15000)) < events.index("target")
```

Use the existing `DelayedRabbitHole` test fake pattern from `tests/test_transactions.py`.

- [ ] **Step 2: Write failing callback-notification tests**

Mirror the household delayed-notification tests with `PhoneSellUnbornNoobooInteraction`: after `_complete_sale`, assert no notification; after `workflow.finish("completed")`, assert the unborn completion notification; after `workflow.finish("failed", "Rabbit hole was canceled")`, assert the failure notification.

- [ ] **Step 3: Run runtime tests and verify RED**

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_runtime.py -k "unborn and (waits or delayed)"
```

Expected: FAIL because unborn runtime uses an immediate collaborator and notifies synchronously.

- [ ] **Step 4: Wire the real adapter and callback**

In `_runtime_services`, replace the unborn no-op collaborator with:

```python
Sims4RabbitHoleAdapter(
    expected_offspring_lookup=pregnancies.expected_offspring_count
)
```

Add `on_finished=None` to `complete_unborn_sale` and pass it to `workflow.confirm_and_complete`. In `_UnbornSaleInteraction._complete_sale`, pass a callback to a new `_on_sale_finished` method. Move the state check, success notification, success log, and failure notification into that callback exactly as the household interaction already does.

- [ ] **Step 5: Run runtime and full tests**

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_runtime.py
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests
```

Expected: PASS; household delayed ordering remains green.

- [ ] **Step 6: Commit runtime ordering**

```powershell
git add src/shady_sim_deals/sims4_runtime.py tests/test_runtime.py
git commit -m "fix: apply unborn sales after rabbit holes"
```

---

### Task 3: Package private unborn rabbit-hole resources

**Files:**
- Create: `tuning/rabbit_holes/unborn_sale_solo_90.xml`
- Create: `tuning/rabbit_holes/unborn_sale_shared_90.xml`
- Create: `tuning/rabbit_holes/unborn_sale_solo_120.xml`
- Create: `tuning/rabbit_holes/unborn_sale_shared_120.xml`
- Create: `tuning/rabbit_holes/unborn_sale_solo_150.xml`
- Create: `tuning/rabbit_holes/unborn_sale_shared_150.xml`
- Create: `tuning/interactions/unborn_rabbit_hole_90.xml`
- Create: `tuning/interactions/unborn_rabbit_hole_120.xml`
- Create: `tuning/interactions/unborn_rabbit_hole_150.xml`
- Modify: `tests/test_build.py`
- Modify: `build_mod.py`

**Interfaces:**
- Produces rabbit-hole IDs `0xEAA21FFB1081E00B` through `0xEAA21FFB1081E010`.
- Produces private affordance IDs `0xEAA21FFB1081E011` through `0xEAA21FFB1081E013`.
- Reuses localized display name `0xA110000B`.

- [ ] **Step 1: Write failing exact-resource and tuning-shape tests**

Extend `EXPECTED_RESOURCE_KEYS` with all nine IDs. Add a test that asserts solo resources use `c="RabbitHole"`, `m="rabbit_hole.rabbit_hole"`; shared resources use `c="TwoSimRabbitHole"`, `m="rabbit_hole.multi_sim_rabbit_hole"`, Actor then PickedSim; and both variants point to their duration's affordance. Assert affordance min/max values are 90, 120, and 150, `_saveable` is disabled, and display name is `0xA110000B`.

Also assert the Lot51 injector still contains only the four public sale interaction IDs.

- [ ] **Step 2: Run build tests and verify RED**

```powershell
$env:PYTHONPATH='.'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_build.py
```

Expected: FAIL because the nine resources are absent.

- [ ] **Step 3: Create the solo and shared rabbit-hole XML**

Use this solo shape, substituting identity and affordance IDs:

```xml
<I c="RabbitHole" i="rabbit_hole" m="rabbit_hole.rabbit_hole" n="ShadySimDeals:UnbornSaleSolo90" s="16907111114276462603">
  <T n="affordance">16907111114276462609</T>
</I>
```

Use this shared shape:

```xml
<I c="TwoSimRabbitHole" i="rabbit_hole" m="rabbit_hole.multi_sim_rabbit_hole" n="ShadySimDeals:UnbornSaleShared90" s="16907111114276462604">
  <T n="affordance">16907111114276462609</T>
  <L n="first_participant_types"><E>Actor</E></L>
  <L n="second_participant_types"><E>PickedSim</E></L>
</I>
```

Create corresponding 120-minute IDs `E00D/E00E -> E012` and 150-minute IDs `E00F/E010 -> E013`.

- [ ] **Step 4: Create the three private affordances**

Copy the existing private household affordance shape, changing name, instance, min/max duration, and display name to `0xA110000B`. Use IDs `E011=90`, `E012=120`, and `E013=150`. Keep `_saveable` disabled, autonomy and user direction false, generic animation factory `23834`, `fade_sim_out=True`, and target type Actor. Do not tune a `rabbit_hole` basic liability; the managed rabbit-hole service owns the lifecycle, and that unregistered variant loads as a string.

- [ ] **Step 5: Add all nine resources to `package_resources()`**

Add explicit `(read_bytes(), RABBIT_HOLE_TYPE or INTERACTION_TUNING_TYPE, 0, instance)` tuples next to the existing household rabbit-hole resources. Do not generate XML or add another packaging abstraction.

- [ ] **Step 6: Run build tests, full tests, and build**

```powershell
$env:PYTHONPATH='.'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_build.py
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests
py -3.12 build_mod.py
```

Expected: all tests PASS and both distributables build.

- [ ] **Step 7: Commit tuning and packaging**

```powershell
git add build_mod.py tests/test_build.py tuning/rabbit_holes tuning/interactions/unborn_rabbit_hole_*.xml
git commit -m "feat: package unborn sale rabbit holes"
```

---

### Task 4: Document and hand off live verification

**Files:**
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`
- Modify: `DEVELOPMENT.md`
- Modify: `SPECS_CHECKLIST.md`

**Interfaces:**
- Consumes: completed runtime, adapter, and packaged tuning behavior.
- Produces: accurate player guidance and live-test checklist.

- [ ] **Step 1: Update documentation without claiming live success**

Document that every sale mutates only after natural rabbit-hole expiration; self-target unborn sales use one Sim; other-target unborn sales use actor plus pregnant Sim and return both; unborn durations are 90/120/150 minutes; cancellation changes nothing. Replace README's statement that unborn sales are immediate.

In `SPECS_CHECKLIST.md`, mark unborn rabbit-hole implementation/package subitems complete but leave new live checks unchecked. Keep household live timing/return checks unchecked until retested.

- [ ] **Step 2: Run documentation and diff checks**

```powershell
rg -n "rabbit|unborn|90|120|150|immediate" README.md ARCHITECTURE.md DEVELOPMENT.md SPECS_CHECKLIST.md
git diff --check
```

- [ ] **Step 3: Run fresh final verification**

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests
py -3.12 build_mod.py
Get-Item dist/ShadySimDeals.package,dist/ShadySimDeals.ts4script | Select-Object Name,Length,LastWriteTime
```

Expected: full suite passes, build exits zero, and both files are current and non-empty.

- [ ] **Step 4: Commit documentation**

```powershell
git add README.md ARCHITECTURE.md DEVELOPMENT.md SPECS_CHECKLIST.md
git commit -m "docs: describe sale rabbit hole ordering"
```

- [ ] **Step 5: Install and perform the live matrix**

Only while `TS4_x64` is closed, run `./install_mod.ps1`. Then verify:

1. Household target remains unsold until the shared rabbit hole expires; only actor returns; transfer then one payment.
2. Pregnant actor enters alone; pregnancy remains active until expiration; actor returns non-pregnant; one payment.
3. Other pregnant target enters with actor; both return; pregnancy ends after expiration; one payment.
4. Cancel each transaction type and confirm no target or funds mutation.
5. Confirm no new `lastException.txt` and inspect `shady_sim_deals.log`.

Record live checklist evidence only after every observed behavior passes.
