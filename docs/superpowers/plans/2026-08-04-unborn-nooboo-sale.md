# Unborn Nooboo Sale Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe immediate **Sell Unborn Nooboo** transaction to phones and compatible computers.

**Architecture:** One shared unborn interaction coordinates native dialogs and delegates to the existing domain services. The verified pregnancy adapter reads public tracker state and clears pregnancy, while the shared orchestrator prepays irreversible targets and compensates failed processing by removing the exact payment.

**Tech Stack:** Python 3.7-compatible game scripts, Python 3.12 with pytest, Sims 4 XML tuning and DBPF resources, Lot51 Core 1.43.

## Global Constraints

- Support The Sims 4 patch `1.125.59.1030`.
- Require Lot51 Core Library `1.43` or newer.
- Use `PregnancyTracker.is_pregnant`, `offspring_count`, and `clear_pregnancy()` only; never remove pregnancy moodlets.
- Never call `create_offspring_data()` while calculating an offer.
- Include the active Sim when pregnant.
- Cancellation must not mutate pregnancy, funds, or reservations.
- Keep household-member transaction ordering unchanged.
- Defer rabbit holes, animations, buffs, relationship reactions, and forced early twin/triplet discovery.

---

### Task 1: Verify pregnancy state and unborn validation

**Files:**
- Modify: `tests/test_sims4_adapters.py`
- Modify: `src/shady_sim_deals/sims4_adapters.py`

**Interfaces:**
- Produces: `Sims4PregnancyAdapter.is_pregnant(sim_id) -> bool`.
- Produces: `Sims4PregnancyAdapter.expected_offspring_count(sim_id) -> int`.
- Produces: `Sims4PregnancyAdapter.conclude_pregnancy(sim_id) -> bool`.
- Extends: `Sims4TransactionValidator(..., pregnancy_check=None)` for `transaction_type == "unborn"`.

- [ ] **Step 1: Write failing pregnancy-adapter tests**

Add a fake tracker that records public API use:

```python
class FakePregnancyTracker:
    def __init__(self, pregnant=True, offspring_count=1, clear_succeeds=True):
        self.is_pregnant = pregnant
        self.offspring_count = offspring_count
        self.clear_succeeds = clear_succeeds
        self.cleared = 0

    def clear_pregnancy(self):
        self.cleared += 1
        if self.clear_succeeds:
            self.is_pregnant = False


def test_pregnancy_adapter_reads_public_count_without_generating_data():
    tracker = FakePregnancyTracker(offspring_count=2)
    sim_info = SimpleNamespace(pregnancy_tracker=tracker)
    adapter = sims4_adapters.Sims4PregnancyAdapter(
        sim_info_lookup=lambda sim_id: sim_info
    )

    assert adapter.expected_offspring_count("pregnant") == 2
    assert not hasattr(tracker, "create_offspring_data")


def test_pregnancy_adapter_clears_and_verifies_pregnancy():
    tracker = FakePregnancyTracker()
    sim_info = SimpleNamespace(pregnancy_tracker=tracker)
    adapter = sims4_adapters.Sims4PregnancyAdapter(
        sim_info_lookup=lambda sim_id: sim_info
    )

    assert adapter.conclude_pregnancy("pregnant") is True
    assert tracker.cleared == 1
    assert adapter.is_pregnant("pregnant") is False


def test_pregnancy_adapter_reports_failed_clear():
    tracker = FakePregnancyTracker(clear_succeeds=False)
    sim_info = SimpleNamespace(pregnancy_tracker=tracker)
    adapter = sims4_adapters.Sims4PregnancyAdapter(
        sim_info_lookup=lambda sim_id: sim_info
    )

    assert adapter.conclude_pregnancy("pregnant") is False
```

- [ ] **Step 2: Write failing unborn-validator tests**

Extend the existing validator test:

```python
def test_unborn_validator_allows_pregnant_actor_and_rejects_ended_pregnancy():
    actor = FakeSimInfo("ADULT", sim_id="actor")
    households = {"home": FakeHousehold()}
    pregnancy = {"actor": True}
    validator = sims4_adapters.Sims4TransactionValidator(
        sim_info_lookup={"actor": actor}.get,
        household_lookup=households.get,
        pregnancy_check=lambda sim_id: pregnancy.get(str(sim_id), False),
        shutdown_check=lambda: False,
    )
    deal = SaleTransaction("unborn", "actor", "actor", "home")

    assert validator.validate(deal) is None
    pregnancy["actor"] = False
    assert validator.validate(deal) == "Selected Sim is no longer pregnant"
```

- [ ] **Step 3: Run the focused tests and verify RED**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_sims4_adapters.py
```

Expected: FAIL because the adapter constructor does not accept a lookup, uses a
nonexistent offspring getter, refuses to clear pregnancy, and the validator
rejects actor-as-target.

- [ ] **Step 4: Implement the verified adapter calls**

Use an injectable lookup and only public tracker members:

```python
class Sims4PregnancyAdapter:
    def __init__(self, sim_info_lookup=None):
        self._sim_info_lookup = sim_info_lookup or self._find_sim_info

    def _tracker(self, sim_id):
        sim_info = self._sim_info_lookup(str(sim_id))
        if sim_info is None:
            raise ValueError("SimInfo no longer exists")
        return getattr(sim_info, "pregnancy_tracker", None)

    def is_pregnant(self, sim_id):
        tracker = self._tracker(sim_id)
        return bool(tracker is not None and tracker.is_pregnant)

    def expected_offspring_count(self, sim_id):
        tracker = self._tracker(sim_id)
        return max(1, int(getattr(tracker, "offspring_count", 1) or 1))

    def conclude_pregnancy(self, sim_id):
        tracker = self._tracker(sim_id)
        if tracker is None or not tracker.is_pregnant:
            return False
        tracker.clear_pregnancy()
        return not bool(tracker.is_pregnant)
```

- [ ] **Step 5: Make validation transaction-type aware**

Add `pregnancy_check` to `Sims4TransactionValidator.__init__` and branch only the
target-specific rules:

```python
self._pregnancy_check = pregnancy_check or (lambda sim_id: False)

if transaction.transaction_type == "unborn":
    if not self._pregnancy_check(transaction.target_id):
        return "Selected Sim is no longer pregnant"
else:
    if transaction.actor_id == transaction.target_id:
        return "The actor cannot be the target"
    if getattr(target, "is_pet", False):
        return "Pets are not supported"
    try:
        age_key(target)
    except ValueError as exc:
        return str(exc)
```

Keep zone, household, funds, membership, and reservation checks shared below
this branch.

- [ ] **Step 6: Run focused and full tests**

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_sims4_adapters.py
py -3.12 -m pytest -q -p no:cacheprovider tests
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add src/shady_sim_deals/sims4_adapters.py tests/test_sims4_adapters.py
git commit -m "feat: add verified pregnancy adapter"
```

---

### Task 2: Compensate irreversible pregnancy processing

**Files:**
- Modify: `tests/test_transactions.py`
- Modify: `tests/test_processors.py`
- Modify: `tests/test_sims4_adapters.py`
- Modify: `src/shady_sim_deals/orchestrator.py`
- Modify: `src/shady_sim_deals/processors.py`
- Modify: `src/shady_sim_deals/sims4_adapters.py`

**Interfaces:**
- Produces: `UnbornTargetProcessor.requires_prepayment = True`.
- Produces: `Sims4FundsAdapter.withdraw(household_id, amount) -> None`.
- Extends: `TransactionOrchestrator.confirm_and_complete()` with compensated prepayment.

- [ ] **Step 1: Write failing prepayment and compensation tests**

Extend `Recorder` with `withdraw`, then add:

```python
def test_irreversible_target_is_prepaid_before_processing():
    events = []
    target = Recorder(events)
    target.requires_prepayment = True
    workflow = TransactionOrchestrator(
        Recorder(events), Recorder(events), Recorder(events), target,
        Recorder(events), Recorder(events),
    )
    deal = SaleTransaction("unborn", "actor", "pregnant", "home")
    workflow.prepare(deal, SaleOffer(15000, {}, "buyer"))

    assert workflow.confirm_and_complete(deal)
    assert events.index(("payment", "home", 15000)) < events.index("target")
    assert deal.payment_completed


def test_failed_irreversible_target_refunds_prepayment():
    events = []
    target = Recorder(events, failure="pregnancy completion failed")
    target.requires_prepayment = True
    funds = Recorder(events)
    workflow = TransactionOrchestrator(
        Recorder(events), Recorder(events), Recorder(events), target,
        funds, Recorder(events),
    )
    deal = SaleTransaction("unborn", "actor", "pregnant", "home")
    workflow.prepare(deal, SaleOffer(15000, {}, "buyer"))

    assert not workflow.confirm_and_complete(deal)
    assert events[-2:] == [("refund", "home", 15000), "release"]
    assert not deal.payment_completed
```

Define the recorder method used above:

```python
def withdraw(self, household_id, amount):
    self.events.append(("refund", household_id, amount))
```

- [ ] **Step 2: Add processor contract test**

```python
def test_unborn_processor_requires_prepayment():
    assert UnbornTargetProcessor.requires_prepayment is True
```

- [ ] **Step 3: Add funds withdrawal test**

```python
def test_funds_adapter_refund_removes_full_marketplace_payment(monkeypatch):
    calls = []
    funds = SimpleNamespace(
        try_remove=lambda amount, reason, sim, require_full: calls.append(
            (amount, reason, sim, require_full)
        ) or True
    )
    household = SimpleNamespace(funds=funds)
    services = SimpleNamespace(
        household_manager=lambda: SimpleNamespace(get=lambda household_id: household)
    )
    consts = SimpleNamespace(TELEMETRY_MONEY_OBJECT_MARKETPLACE_SALE=25)
    monkeypatch.setitem(sys.modules, "services", services)
    monkeypatch.setitem(
        sys.modules, "protocolbuffers", SimpleNamespace(Consts_pb2=consts)
    )

    sims4_adapters.Sims4FundsAdapter().withdraw("7", 15000)

    assert calls == [(15000, 25, None, True)]
```

- [ ] **Step 4: Run focused tests and verify RED**

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_transactions.py tests/test_processors.py tests/test_sims4_adapters.py
```

Expected: FAIL because prepayment, refund, processor metadata, and withdrawal do
not exist.

- [ ] **Step 5: Implement prepayment in the shared orchestrator**

In `confirm_and_complete`, set `prepaid = False` before the `try`. Immediately
before target processing:

```python
requires_prepayment = bool(
    getattr(self._target_processor, "requires_prepayment", False)
)
if requires_prepayment and not transaction.payment_completed:
    self._funds.deposit(transaction.household_id, transaction.offer.amount)
    transaction.payment_completed = True
    prepaid = True

self._target_processor.process(transaction)
target_processed = True
```

Leave the existing post-target deposit in place; its
`if not transaction.payment_completed` guard skips a second payment.

At the start of the exception handler, compensate only a failed prepaid target:

```python
if prepaid and not target_processed and transaction.payment_completed:
    try:
        self._funds.withdraw(transaction.household_id, transaction.offer.amount)
        transaction.payment_completed = False
    except Exception as refund_exc:
        transaction.failure_reason += "; refund failed: {}".format(refund_exc)
elif target_processed and not transaction.payment_completed:
    # Keep the existing reversible target rollback block unchanged.
```

- [ ] **Step 6: Mark the unborn processor and add full withdrawal**

```python
class UnbornTargetProcessor:
    requires_prepayment = True
```

Add to `Sims4FundsAdapter`:

```python
def withdraw(self, household_id, amount):
    import services
    from protocolbuffers import Consts_pb2

    household = services.household_manager().get(int(household_id))
    if household is None or getattr(household, "funds", None) is None:
        raise ValueError("Household funds are unavailable")
    if not household.funds.try_remove(
        int(amount),
        Consts_pb2.TELEMETRY_MONEY_OBJECT_MARKETPLACE_SALE,
        None,
        True,
    ):
        raise RuntimeError("The prepaid amount could not be refunded")
```

- [ ] **Step 7: Run focused and full tests**

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_transactions.py tests/test_processors.py tests/test_sims4_adapters.py
py -3.12 -m pytest -q -p no:cacheprovider tests
```

Expected: PASS, with existing household target-before-payment tests unchanged.

- [ ] **Step 8: Commit**

```powershell
git add src/shady_sim_deals/orchestrator.py src/shady_sim_deals/processors.py src/shady_sim_deals/sims4_adapters.py tests/test_transactions.py tests/test_processors.py tests/test_sims4_adapters.py
git commit -m "feat: compensate irreversible pregnancy transactions"
```

---

### Task 3: Add the shared unborn picker and transaction flow

**Files:**
- Modify: `tests/test_runtime.py`
- Modify: `src/shady_sim_deals/sims4_runtime.py`

**Interfaces:**
- Produces: `eligible_unborn_ids(...) -> tuple[str, ...]`.
- Produces: `build_unborn_candidate(sim_info, pregnancy_adapter) -> SaleCandidate`.
- Produces: `complete_unborn_sale(...) -> SaleTransaction`.
- Produces: `_UnbornSaleInteraction` shared by phone and computer.

- [ ] **Step 1: Write failing eligibility and offer tests**

Extend `FakeSimInfo` with `pregnant=False` and a fake pregnancy adapter:

```python
class FakePregnancies:
    def __init__(self, pregnant_ids=(), counts=None):
        self.pregnant_ids = {str(sim_id) for sim_id in pregnant_ids}
        self.counts = counts or {}

    def is_pregnant(self, sim_id):
        return str(sim_id) in self.pregnant_ids

    def expected_offspring_count(self, sim_id):
        return self.counts.get(str(sim_id), 1)


def test_unborn_candidates_include_pregnant_actor_and_household_member():
    sims = (
        FakeSimInfo("actor"),
        FakeSimInfo("pregnant"),
        FakeSimInfo("not-pregnant"),
        FakeSimInfo("elsewhere", household_id="other"),
    )
    pregnancies = FakePregnancies(("actor", "pregnant", "elsewhere"))

    assert sims4_runtime.eligible_unborn_ids(
        sims,
        household_id="home",
        pregnancy_check=pregnancies.is_pregnant,
        sold_check=lambda sim_id: False,
        reserved_check=lambda sim_id: False,
    ) == ("actor", "pregnant")


def test_build_unborn_candidate_uses_public_offspring_count():
    target = FakeSimInfo("pregnant")
    pregnancies = FakePregnancies(("pregnant",), {"pregnant": 2})

    candidate = sims4_runtime.build_unborn_candidate(target, pregnancies)

    assert candidate.age == "unborn"
    assert candidate.expected_offspring == 2
```

- [ ] **Step 2: Write failing shared-entry and completion tests**

```python
def test_phone_and_computer_unborn_sales_share_one_implementation():
    shared = sims4_runtime._UnbornSaleInteraction

    assert issubclass(sims4_runtime.PhoneSellUnbornNoobooInteraction, shared)
    assert issubclass(sims4_runtime.ComputerSellUnbornNoobooInteraction, shared)


def test_complete_unborn_sale_uses_unborn_pricing_and_workflow():
    events = []
    recorder = RuntimeRecorder(events)
    recorder.requires_prepayment = True
    recorder.withdraw = lambda household_id, amount: events.append(
        ("refund", household_id, amount)
    )
    workflow = TransactionOrchestrator(
        recorder, recorder, recorder, recorder, recorder, recorder
    )
    target = FakeSimInfo("pregnant")
    pregnancies = FakePregnancies(("pregnant",), {"pregnant": 2})

    deal = sims4_runtime.complete_unborn_sale(
        "actor", "pregnant", "home", lambda sim_id: target,
        pregnancies, workflow, SimSalePricingService(),
    )

    assert deal.state == "completed"
    assert deal.offer.amount == 27000
```

Add a picker test equivalent to the existing computer household picker test,
instantiating `PhoneSellUnbornNoobooInteraction` with a pregnant actor and
asserting one picker row tagged with the actor ID.

- [ ] **Step 3: Run runtime tests and verify RED**

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_runtime.py
```

Expected: FAIL because the unborn helper functions and shared interaction do not
exist.

- [ ] **Step 4: Add pure runtime helpers**

Implement `eligible_unborn_ids` by constructing `SimRecord` values with
`pregnant=pregnancy_check(sim_id)` and passing them to `unborn_candidates`.
Use the same invalid/destroyed, sold, reserved, pet, and household checks as the
household picker, without calling `age_key`.

Implement:

```python
def build_unborn_candidate(sim_info, pregnancy_adapter):
    return SaleCandidate(
        sim_info.sim_id,
        "{} {}".format(sim_info.first_name, sim_info.last_name).strip(),
        "unborn",
        expected_offspring=pregnancy_adapter.expected_offspring_count(
            sim_info.sim_id
        ),
    )
```

`complete_unborn_sale` mirrors `complete_household_sale` but calls
`calculate_unborn_offer` and creates `SaleTransaction("unborn", ...)`.

- [ ] **Step 5: Compose the unborn runtime workflow**

In `_runtime_services`, create one `Sims4PregnancyAdapter`, one transaction-aware
validator using `pregnancy_check=pregnancies.is_pregnant`, one
`UnbornTargetProcessor`, and an `unborn_workflow` sharing reservations, funds,
rabbit-hole placeholder, and consequences placeholder with the household flow.
Store `pregnancies` and `unborn_workflow` in `RUNTIME`.

- [ ] **Step 6: Implement `_UnbornSaleInteraction`**

Use the existing household interaction as the exact UI pattern, with these
differences:

- candidates come from `eligible_unborn_ids`;
- picker strings are `unborn_picker_title` and `unborn_picker_body`;
- offers use `build_unborn_candidate` and `calculate_unborn_offer`;
- completion calls `complete_unborn_sale` with `unborn_workflow`;
- notification keys are `completion_unborn_title` and `completion_unborn_body`.

Then define only thin entry classes:

```python
class PhoneSellUnbornNoobooInteraction(_UnbornSaleInteraction):
    entry_point = "phone"


class ComputerSellUnbornNoobooInteraction(_UnbornSaleInteraction):
    entry_point = "computer"
```

- [ ] **Step 7: Run focused and full tests**

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_runtime.py
py -3.12 -m pytest -q -p no:cacheprovider tests
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add src/shady_sim_deals/sims4_runtime.py tests/test_runtime.py
git commit -m "feat: add shared unborn sale flow"
```

---

### Task 4: Package and localize both unborn entry points

**Files:**
- Modify: `tests/test_build.py`
- Modify: `build_mod.py`
- Modify: `localization/en_us.json`
- Modify: `src/shady_sim_deals/localization.py`
- Modify: `tuning/interactions/phone_sell_unborn_nooboo.xml`
- Modify: `tuning/interactions/computer_sell_unborn_nooboo.xml`
- Modify: `tuning/snippets/lot51_phone_injector.xml`

**Interfaces:**
- Produces: phone unborn interaction `0xEAA21FFB1081E002`.
- Produces: computer unborn interaction `0xEAA21FFB1081E004`.
- Produces: localization keys `0xA1100016` and `0xA1100017`.

- [ ] **Step 1: Write failing package tests**

Extend the exact package resource set with:

```python
(0xE882D22F, 0, 0xEAA21FFB1081E002),
(0xE882D22F, 0, 0xEAA21FFB1081E004),
```

Update the injector test to assert both phone IDs under `phone_affordances` and
both computer IDs under `inject_by_object_tags/affordances`. Add:

```python
def test_unborn_interactions_use_shady_sim_deals_category():
    unborn_ids = {0xEAA21FFB1081E002, 0xEAA21FFB1081E004}
    interactions = {
        instance: ET.fromstring(data)
        for data, resource_type, _, instance in build_mod.package_resources()
        if resource_type == build_mod.INTERACTION_TUNING_TYPE
        and instance in unborn_ids
    }

    assert set(interactions) == unborn_ids
    assert all(
        int(xml.find("./T[@n='category']").text) == build_mod.CUSTOM_CATEGORY_ID
        for xml in interactions.values()
    )
```

- [ ] **Step 2: Run build tests and verify RED**

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_build.py
```

Expected: FAIL because neither unborn interaction is packaged or injected.

- [ ] **Step 3: Tune and inject both interactions**

Add the existing custom category to each unborn interaction:

```xml
<T n="category">16906829660497641488</T>
```

Add `16907111114276462594` to the existing `phone_affordances` list and
`16907111114276462596` to the existing computer `affordances` list.

- [ ] **Step 4: Package both XML resources**

Add their XML bytes to `package_resources()` using
`0xEAA21FFB1081E002` and `0xEAA21FFB1081E004`, next to their corresponding
household interactions.

- [ ] **Step 5: Add picker localization**

Add:

```json
"0xA1100016": "Select a Prenatal Business Partner",
"0xA1100017": "Choose the pregnant household member whose future nursery expenses have become negotiable."
```

Map these in `src/shady_sim_deals/localization.py`:

```python
"unborn_picker_title": 0xA1100016,
"unborn_picker_body": 0xA1100017,
```

Include `src/shady_sim_deals/localization.py` in this task's commit.

- [ ] **Step 6: Run build tests and full suite**

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_build.py
py -3.12 -m pytest -q -p no:cacheprovider tests
```

Expected: PASS with eight DBPF resources total.

- [ ] **Step 7: Commit**

```powershell
git add build_mod.py localization/en_us.json src/shady_sim_deals/localization.py tests/test_build.py tuning/interactions/phone_sell_unborn_nooboo.xml tuning/interactions/computer_sell_unborn_nooboo.xml tuning/snippets/lot51_phone_injector.xml
git commit -m "feat: package unborn Nooboo sales"
```

---

### Task 5: Document, build, install, and verify in game

**Files:**
- Modify: `README.md`
- Modify: `DEVELOPMENT.md`
- Modify: `ARCHITECTURE.md`
- Modify: `SPECS_CHECKLIST.md`
- Verify: `dist/ShadySimDeals.package`
- Verify: `dist/ShadySimDeals.ts4script`

**Interfaces:**
- Consumes: all completed unborn runtime and tuning changes.
- Produces: updated implementation status and live verification record.

- [ ] **Step 1: Update documentation**

Document the phone/computer unborn flow, immediate pregnancy conclusion, public
offspring-count limitation, and prepayment compensation. In
`SPECS_CHECKLIST.md`:

- check the packaged/unit-tested unborn entry point, pregnant picker, verified
  pregnancy adapter, and public multiplicity pricing sub-items;
- leave real unborn rabbit hole, buffs, reactions, forced early multiplicity,
  and live acceptance items unchecked;
- add unchecked live checks for both actor and other-household-member pregnancy.

- [ ] **Step 2: Verify documentation and diff integrity**

```powershell
rg -n "Unborn|pregnan|offspring|prepay|refund" README.md DEVELOPMENT.md ARCHITECTURE.md SPECS_CHECKLIST.md
git diff --check
```

Expected: current capabilities and limitations agree across all four documents.

- [ ] **Step 3: Commit documentation**

```powershell
git add README.md DEVELOPMENT.md ARCHITECTURE.md SPECS_CHECKLIST.md
git commit -m "docs: describe unborn Nooboo sales"
```

- [ ] **Step 4: Run final automated verification and build**

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests
py -3.12 build_mod.py
Get-Item dist/ShadySimDeals.package,dist/ShadySimDeals.ts4script | Select-Object Name,Length,LastWriteTime
```

Expected: all tests pass and both artifacts are current and non-empty.

- [ ] **Step 5: Install only while the game is closed**

Confirm `Get-Process TS4_x64 -ErrorAction SilentlyContinue` returns nothing, then:

```powershell
.\install_mod.ps1
```

- [ ] **Step 6: Perform live smoke tests**

1. Load a household containing a pregnant active Sim and another pregnant Sim.
2. Verify both phone and computer expose **Sell Unborn Nooboo**.
3. Verify the picker includes both pregnant Sims and excludes non-pregnant Sims.
4. Cancel the picker and confirmation once; verify pregnancy and funds are unchanged.
5. Sell the active Sim's unborn Nooboo; verify pregnancy ends and payment occurs once.
6. Reload or create another pregnancy, sell the other pregnant household member's
   unborn Nooboo, and verify that pregnancy ends and payment occurs once.
7. Check `lastException.txt`, `ShadySimDeals.log`, and `lot51_core.log`.

- [ ] **Step 7: Record only confirmed live criteria**

After successful live tests, check acceptance criteria 3, 5, and 12 plus the
corresponding live checklist sub-items. Keep criteria 8, 9, 13, 14, and 15
unchecked. Commit the evidence:

```powershell
git add SPECS_CHECKLIST.md
git commit -m "docs: confirm unborn sales in game"
```
