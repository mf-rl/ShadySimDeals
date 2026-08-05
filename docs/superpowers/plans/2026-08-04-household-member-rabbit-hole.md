# Household-Member Rabbit-Hole Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Run household-member sales through a real age-timed shared rabbit hole, then transfer the target and pay exactly once after natural expiration.

**Architecture:** TransactionOrchestrator keeps transaction ordering but pauses after rabbit-hole startup until its collaborator invokes a completion callback. Sims4RabbitHoleAdapter selects one of three private TwoSimRabbitHole tunings from target age and sends actor then target through EA's shared service; unborn sales keep an immediate collaborator.

**Tech Stack:** Python 3.7-compatible Sims 4 scripts, pytest on Python 3.12, Sims 4 interaction and rabbit-hole XML, DBPF packaging, Lot51 Core 1.43+

## Global Constraints

- Support The Sims 4 patch 1.125.59.1030.
- Game-side Python must remain compatible with Python 3.7.
- Lot51 Core 1.43 or newer remains the only mod dependency.
- Household durations remain 75 minutes for elders, 90 for baby through child, and 120 for teen through adult.
- Transfer and payment occur only after natural rabbit-hole expiration.
- Cancellation or startup failure releases reservations without transfer or payment.
- Unborn-Nooboo behavior remains immediate.
- Use private instance IDs 0xEAA21FFB1081E005 through 0xEAA21FFB1081E00A only.

---

### Task 1: Pause transaction completion behind the rabbit-hole callback

**Files:**
- Modify: tests/test_transactions.py
- Modify: src/shady_sim_deals/orchestrator.py

**Interfaces:**
- Consumes: rabbit_holes.run(transaction, on_finished) returning True for asynchronous startup, None for immediate completion, or False for rejected startup.
- Produces: TransactionOrchestrator.confirm_and_complete(transaction, on_finished=None).

- [ ] **Step 1: Write failing delayed-completion and cancellation tests**

Add a DelayedRabbitHole fake and tests:

```python
class DelayedRabbitHole:
    def __init__(self, events, starts=True):
        self.events = events
        self.starts = starts
        self.callback = None

    def run(self, transaction, on_finished):
        self.events.append("rabbit_hole")
        self.callback = on_finished
        return self.starts


def test_household_completion_waits_for_rabbit_hole_expiration():
    events = []
    rabbit_hole = DelayedRabbitHole(events)
    workflow = TransactionOrchestrator(
        Recorder(events), Recorder(events), rabbit_hole,
        Recorder(events), Recorder(events), Recorder(events),
    )
    deal = transaction()
    workflow.prepare(deal, SaleOffer(5000, {}, "buyer"))

    assert workflow.confirm_and_complete(deal)
    assert deal.state == "rabbit_hole_started"
    assert "target" not in events
    assert ("payment", "home", 5000) not in events

    rabbit_hole.callback(canceled=False)

    assert deal.state == "completed"
    assert events.index("target") < events.index(("payment", "home", 5000))
    assert events[-1] == "release"


def test_cancelled_rabbit_hole_does_not_process_or_pay():
    events = []
    rabbit_hole = DelayedRabbitHole(events)
    workflow = TransactionOrchestrator(
        Recorder(events), Recorder(events), rabbit_hole,
        Recorder(events), Recorder(events), Recorder(events),
    )
    deal = transaction()
    workflow.prepare(deal, SaleOffer(5000, {}, "buyer"))
    workflow.confirm_and_complete(deal)

    rabbit_hole.callback(canceled=True)

    assert deal.state == "failed"
    assert deal.failure_reason == "Rabbit hole was canceled"
    assert "target" not in events
    assert not any(isinstance(event, tuple) and event[0] == "payment" for event in events)
    assert events[-1] == "release"
```

Change Recorder.run to accept on_finished and return None so existing tests model immediate completion:

```python
def run(self, transaction, on_finished):
    self.events.append("rabbit_hole")
    return None
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_transactions.py
```

Expected: callback argument errors and immediate tests no longer reach target processing.

- [ ] **Step 3: Split startup from terminal completion**

In confirm_and_complete, keep validation, reservation, and player_confirmed transition. Pass a callback to self._rabbit_holes.run, reject an explicit False, transition to rabbit_hole_started, and invoke the callback only when run returns None:

```python
def confirm_and_complete(self, transaction, on_finished=None):
    if transaction.state == "completed":
        return True
    if transaction.state != "offer_calculated":
        raise TransactionError("Transaction is not ready for confirmation")
    try:
        error = self._validator.validate(transaction)
        if error:
            raise TransactionError(str(error))
        self._reservations.reserve(transaction)
        self._states.transition(transaction, "player_confirmed")
        callback = lambda canceled=False: self._finish_after_rabbit_hole(
            transaction, canceled, on_finished
        )
        started = self._rabbit_holes.run(transaction, callback)
        if started is False:
            raise TransactionError("Rabbit hole could not start")
        self._states.transition(transaction, "rabbit_hole_started")
        if started is None:
            callback()
        return transaction.state in ("rabbit_hole_started", "completed")
    except Exception as exc:
        self._fail_before_target(transaction, exc, on_finished)
        return False
```

Move the existing target, payment, consequence, refund, and rollback block into
_finish_after_rabbit_hole. On canceled=True set failure_reason to
"Rabbit hole was canceled", transition to failed, release, and notify. Guard
against duplicate callbacks unless state is rabbit_hole_started. Add
_fail_before_target to transition nonterminal transactions to failed, release,
and invoke on_finished after terminal state is set.

- [ ] **Step 4: Run focused and full tests**

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_transactions.py
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests
```

Expected: all tests pass; payment rollback and unborn prepayment ordering remain unchanged.

- [ ] **Step 5: Commit**

```powershell
git add src/shady_sim_deals/orchestrator.py tests/test_transactions.py
git commit -m "refactor: await rabbit hole completion"
```

---

### Task 2: Implement the shared Sims 4 rabbit-hole adapter

**Files:**
- Modify: tests/test_sims4_adapters.py
- Modify: src/shady_sim_deals/sims4_adapters.py

**Interfaces:**
- Produces: Sims4RabbitHoleAdapter.run(transaction, on_finished) -> bool.
- Consumes: services.get_rabbit_hole_service(), Types.RABBIT_HOLE instance manager, age_key, and the three tuned rabbit-hole IDs.

- [ ] **Step 1: Write failing adapter tests**

Create fake service and manager objects, then add:

```python
@pytest.mark.parametrize(
    ("age", "expected_type"),
    (
        ("ELDER", 0xEAA21FFB1081E005),
        ("BABY", 0xEAA21FFB1081E006),
        ("CHILD", 0xEAA21FFB1081E006),
        ("TEEN", 0xEAA21FFB1081E007),
        ("ADULT", 0xEAA21FFB1081E007),
    ),
)
def test_rabbit_hole_adapter_starts_one_shared_hole_in_participant_order(age, expected_type):
    actor = FakeSimInfo("ADULT", sim_id="1")
    target = FakeSimInfo(age, sim_id="2")
    callbacks = []
    service = FakeRabbitHoleService()
    adapter = sims4_adapters.Sims4RabbitHoleAdapter(
        rabbit_hole_service=service,
        sim_info_lookup={"1": actor, "2": target}.get,
        rabbit_hole_lookup=lambda instance: instance,
    )
    deal = SaleTransaction("household_member", "1", "2", "home")

    assert adapter.run(deal, callbacks.append) is True
    assert service.started == [([actor, target], expected_type)]
    assert service.callback_key == (actor.sim_id, service.rabbit_hole_id)

    service.callback(canceled=False)
    assert callbacks == [False]
```

Add separate tests asserting a missing participant raises IntegrationUnavailable,
a None startup result raises, and callback-registration failure removes the
shared rabbit hole with canceled=True.

- [ ] **Step 2: Run adapter tests and verify RED**

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_sims4_adapters.py
```

Expected: Sims4RabbitHoleAdapter has no injectable implementation or mapping.

- [ ] **Step 3: Implement the minimum adapter**

Replace the placeholder with:

```python
class Sims4RabbitHoleAdapter:
    RABBIT_HOLE_BY_AGE = {
        "elder": 0xEAA21FFB1081E005,
        "baby": 0xEAA21FFB1081E006,
        "infant": 0xEAA21FFB1081E006,
        "toddler": 0xEAA21FFB1081E006,
        "child": 0xEAA21FFB1081E006,
        "teen": 0xEAA21FFB1081E007,
        "young_adult": 0xEAA21FFB1081E007,
        "adult": 0xEAA21FFB1081E007,
    }

    def __init__(
        self,
        rabbit_hole_service=None,
        sim_info_lookup=None,
        rabbit_hole_lookup=None,
    ):
        self._service = rabbit_hole_service
        self._sim_info_lookup = sim_info_lookup or Sims4PregnancyAdapter._find_sim_info
        self._rabbit_hole_lookup = rabbit_hole_lookup or self._find_rabbit_hole

    def run(self, transaction, on_finished):
        actor = self._sim_info_lookup(str(transaction.actor_id))
        target = self._sim_info_lookup(str(transaction.target_id))
        if actor is None or target is None:
            raise IntegrationUnavailable("Rabbit-hole participant no longer exists")
        rabbit_hole_type = self._rabbit_hole_lookup(
            self.RABBIT_HOLE_BY_AGE[age_key(target)]
        )
        if rabbit_hole_type is None:
            raise IntegrationUnavailable("Rabbit-hole tuning is unavailable")
        service = self._service or self._find_service()
        rabbit_hole_id = service.put_sims_in_shared_rabbithole(
            [actor, target], rabbit_hole_type
        )
        if rabbit_hole_id is None:
            raise IntegrationUnavailable("Rabbit hole could not start")
        try:
            service.set_rabbit_hole_expiration_callback(
                actor.sim_id,
                rabbit_hole_id,
                lambda canceled=False, **kwargs: on_finished(canceled),
            )
        except Exception:
            service.remove_sim_from_rabbit_hole(
                actor.sim_id, rabbit_hole_id, canceled=True
            )
            raise
        return True

    @staticmethod
    def _find_service():
        import services
        return services.get_rabbit_hole_service()

    @staticmethod
    def _find_rabbit_hole(instance_id):
        import services
        import sims4.resources
        return services.get_instance_manager(
            sims4.resources.Types.RABBIT_HOLE
        ).get(instance_id)
```

- [ ] **Step 4: Run adapter and full tests**

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_sims4_adapters.py
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests
```

- [ ] **Step 5: Commit**

```powershell
git add src/shady_sim_deals/sims4_adapters.py tests/test_sims4_adapters.py
git commit -m "feat: add shared rabbit hole adapter"
```

---

### Task 3: Wire asynchronous household completion into the runtime

**Files:**
- Modify: tests/test_runtime.py
- Modify: src/shady_sim_deals/sims4_runtime.py

**Interfaces:**
- Extends: complete_household_sale(..., on_finished=None).
- Produces: _HouseholdMemberSaleInteraction._on_sale_finished(transaction, target_id).

- [ ] **Step 1: Write failing runtime tests**

Add a delayed workflow fake and prove _complete_sale does not notify before its
callback. Then invoke the callback with a completed transaction and assert the
completion notification is shown. Add a failed callback case asserting the
failure notification.

Update RuntimeRecorder.run to accept on_finished and return None. Update direct
complete_household_sale tests to keep immediate completion.

- [ ] **Step 2: Run runtime tests and verify RED**

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_runtime.py
```

Expected: complete_household_sale rejects on_finished and _complete_sale still
expects immediate completed state.

- [ ] **Step 3: Wire the adapters and callback**

Import Sims4RabbitHoleAdapter. In _runtime_services, pass
Sims4RabbitHoleAdapter() to the household workflow. Change the unborn no-op to:

```python
SimpleNamespace(run=lambda transaction, on_finished: None)
```

Add on_finished=None to complete_household_sale and pass it to
workflow.confirm_and_complete. In _complete_sale, pass:

```python
lambda transaction: self._on_sale_finished(transaction, str(target_id))
```

Move the immediate state check, completion notification, success log, failure
notification, and failure log into _on_sale_finished. Keep its try/except
boundary so UI failures do not escape into RabbitHoleService callbacks.

- [ ] **Step 4: Run runtime and full tests**

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_runtime.py
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests
```

- [ ] **Step 5: Commit**

```powershell
git add src/shady_sim_deals/sims4_runtime.py tests/test_runtime.py
git commit -m "feat: finish household sales after rabbit holes"
```

---

### Task 4: Package the private rabbit-hole tunings

**Files:**
- Create: tuning/rabbit_holes/household_sale_elder.xml
- Create: tuning/rabbit_holes/household_sale_child.xml
- Create: tuning/rabbit_holes/household_sale_adult.xml
- Create: tuning/interactions/household_rabbit_hole_75.xml
- Create: tuning/interactions/household_rabbit_hole_90.xml
- Create: tuning/interactions/household_rabbit_hole_120.xml
- Modify: build_mod.py
- Modify: tests/test_build.py

**Interfaces:**
- Produces rabbit-hole IDs E005-E007 and affordance IDs E008-E00A.
- Adds build_mod.RABBIT_HOLE_TYPE = 0xB16AD2FA.

- [ ] **Step 1: Write failing package tests**

Extend the exact resource set by six keys. Assert each rabbit-hole XML uses
TwoSimRabbitHole, references its paired affordance, maps Actor and PickedSim,
and each affordance has one time_based EXIT_NATURALLY condition with matching
min/max minutes. Assert the Lot51 injector sets remain exactly the existing four
public actions.

- [ ] **Step 2: Run build tests and verify RED**

```powershell
$env:PYTHONPATH='.'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_build.py
```

- [ ] **Step 3: Create the three rabbit-hole resources**

Use this shape with the corresponding IDs and affordance references:

```xml
<I c="TwoSimRabbitHole" i="rabbit_hole" m="rabbit_hole.multi_sim_rabbit_hole" n="ShadySimDeals:HouseholdSaleElder" s="16907111114276462597">
  <T n="affordance">16907111114276462600</T>
  <L n="first_participant_types"><E>Actor</E></L>
  <L n="second_participant_types"><E>PickedSim</E></L>
</I>
```

Child uses E006 -> E009; adult uses E007 -> E00A.

- [ ] **Step 4: Create the three private affordances**

Use this verified base-game rabbit-hole shape, changing name, ID, and both time
values to 75, 90, or 120:

```xml
<I c="SuperInteraction" i="interaction" m="interactions.base.super_interaction" n="ShadySimDeals:HouseholdRabbitHole75" s="16907111114276462600">
  <V n="_saveable" t="enabled" />
  <T n="allow_autonomous">False</T>
  <T n="allow_user_directed">False</T>
  <V n="basic_content" t="flexible_length">
    <U n="flexible_length">
      <L n="conditional_actions">
        <V t="literal"><U n="literal"><L n="conditions">
          <V t="time_based"><U n="time_based"><T n="max_time">75</T><T n="min_time">75</T></U></V>
        </L><E n="interaction_action">EXIT_NATURALLY</E></U></V>
      </L>
      <V n="content" t="looping_content"><U n="looping_content"><U n="animation_ref"><T n="factory">23834</T></U></U></V>
    </U>
  </V>
  <L n="basic_liabilities"><V t="rabbit_hole" /></L>
  <T n="display_name">0xA110000A</T>
  <T n="fade_sim_out">True</T>
  <E n="target_type">ACTOR</E>
</I>
```

- [ ] **Step 5: Package the six resources**

Add RABBIT_HOLE_TYPE and six read_bytes tuples to package_resources, keeping the
existing interaction/category/injector/STBL resources unchanged.

- [ ] **Step 6: Run build and full tests**

```powershell
$env:PYTHONPATH='.'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_build.py
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests
```

- [ ] **Step 7: Commit**

```powershell
git add build_mod.py tests/test_build.py tuning/rabbit_holes tuning/interactions/household_rabbit_hole_75.xml tuning/interactions/household_rabbit_hole_90.xml tuning/interactions/household_rabbit_hole_120.xml
git commit -m "feat: package household sale rabbit holes"
```

---

### Task 5: Document, build, and hand off live verification

**Files:**
- Modify: README.md
- Modify: DEVELOPMENT.md
- Modify: ARCHITECTURE.md
- Modify: SPECS_CHECKLIST.md
- Generate: dist/ShadySimDeals.package
- Generate: dist/ShadySimDeals.ts4script

**Interfaces:**
- Consumes Tasks 1-4.
- Produces accurate implementation status and installable artifacts.

- [ ] **Step 1: Update documentation**

Document household age durations, shared seller/target rabbit hole, delayed
transfer/payment, natural completion, and cancellation safety. Keep unborn sales
documented as immediate. Record the verified service methods, TwoSimRabbitHole
module, resource type 0xB16AD2FA, generic animation 23834, and private IDs.

In SPECS_CHECKLIST.md check the implemented household rabbit-hole item and add
checked automated/package subitems. Leave acceptance criteria 8 and 9 unchecked
with live child/adult/elder subitems.

- [ ] **Step 2: Run documentation and diff checks**

```powershell
rg -n "rabbit|75|90|120|TwoSimRabbitHole|B16AD2FA" README.md DEVELOPMENT.md ARCHITECTURE.md SPECS_CHECKLIST.md
git diff --check
```

- [ ] **Step 3: Run final automated verification and build**

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests
py -3.12 build_mod.py
Get-Item dist/ShadySimDeals.package,dist/ShadySimDeals.ts4script | Select-Object Name,Length,LastWriteTime
```

- [ ] **Step 4: Commit**

```powershell
git add README.md DEVELOPMENT.md ARCHITECTURE.md SPECS_CHECKLIST.md
git commit -m "docs: describe household sale rabbit holes"
```

- [ ] **Step 5: Live verification after the game is closed and artifacts are installed**

Install with .\install_mod.ps1 only while TS4_x64 is not running. In a
disposable save, complete child, adult, and elder sales. Confirm both Sims leave,
the duration is respectively 90, 120, and 75 Sim minutes, only the seller
returns, the target moves to holdings, payment occurs once after expiration,
cancellation makes no changes, and no lastException is generated.

Only after those checks pass, check acceptance criteria 8 and 9 and commit the
live evidence separately.
