# Phone Household Sale Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a playable, phone-only ShadySimDeals interaction for selling Teen-through-Elder household members on The Sims 4 patch 1.125.59.1030.

**Architecture:** Lot51 Core 1.43 injects one custom interaction into the Sim object's phone affordance list. The interaction uses native picker and confirmation dialogs, then delegates filtering, pricing, transfer, rollback, and payment to the existing ShadySimDeals domain and adapter layers.

**Tech Stack:** Python 3.7 game bytecode, Python 3.12 host tests, pytest, Sims 4 XML tuning, DBPF package resources, Lot51 Core TuningInjector.

## Global Constraints

- Support The Sims 4 patch 1.125.59.1030 and Python 3.7 bytecode.
- Require Lot51 Core 1.43 or newer; do not redistribute it.
- Expose only phone household-member sales in this release.
- Allow only Teen, Young Adult, Adult, and Elder targets.
- Preserve SimInfo, genealogy, and relationships; never hard-delete a target.
- Deposit payment only after verified transfer and never more than once.
- Use localized strings for every player-visible label and message.
- Do not use process-memory writes or guessed rabbit-hole APIs.

---

## File Map

- `src/shady_sim_deals/filtering.py`: shared candidate-age and household filtering.
- `src/shady_sim_deals/orchestrator.py`: payment-failure rollback hook.
- `src/shady_sim_deals/processors.py`: sold-target rollback behavior.
- `src/shady_sim_deals/sims4_adapters.py`: current-patch validation, holding-household transfer, rollback, and age conversion.
- `src/shady_sim_deals/sims4_runtime.py`: phone picker, confirmation, service wiring, and notifications.
- `src/shady_sim_deals/localization.py`: stable keys for new picker and dependency strings.
- `tuning/interactions/phone_sell_household_member.xml`: playable interaction tuning.
- `tuning/categories/shady_sim_deals.xml`: phone pie-menu category.
- `tuning/snippets/lot51_phone_injector.xml`: Lot51 phone-affordance injection.
- `localization/en_us.json`: English strings.
- `build_mod.py`: STBL encoding and generic DBPF resource packaging.
- `tests/test_domain.py`: candidate filtering tests.
- `tests/test_transactions.py`: payment rollback test.
- `tests/test_processors.py`: processor rollback test.
- `tests/test_sims4_adapters.py`: fake-game transfer and rollback tests.
- `tests/test_runtime.py`: import-safe runtime flow tests.
- `tests/test_build.py`: package resource and STBL validation.
- `README.md`, `DEVELOPMENT.md`, `ARCHITECTURE.md`: player/developer documentation.

---

### Task 1: Restrict the playable candidate set

**Files:**
- Modify: `src/shady_sim_deals/filtering.py`
- Modify: `src/shady_sim_deals/config.py`
- Test: `tests/test_domain.py`

**Interfaces:**
- Produces: `config.HOUSEHOLD_SALE_AGES`
- Produces: `household_member_candidates(records, actor_id, household_id)` filtering by configured age.

- [ ] **Step 1: Write the failing age-filter test**

Add a test that constructs one SimRecord per age and asserts the result is exactly `teen`, `young_adult`, `adult`, and `elder`.

```python
def test_playable_household_picker_is_teen_through_elder():
    ages = ("baby", "infant", "toddler", "child", "teen", "young_adult", "adult", "elder")
    records = tuple(SimRecord(age, "home", age=age) for age in ages)
    assert [r.age for r in household_member_candidates(records, "actor", "home")] == [
        "teen", "young_adult", "adult", "elder"
    ]
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `py -3.12 -m pytest -q -p no:cacheprovider tests/test_domain.py::test_playable_household_picker_is_teen_through_elder`

Expected: FAIL because younger ages are currently returned.

- [ ] **Step 3: Add the immutable configured age set and one filter predicate**

Add `HOUSEHOLD_SALE_AGES = frozenset(("teen", "young_adult", "adult", "elder"))` to `config.py`, import config in `filtering.py`, and require `record.age in config.HOUSEHOLD_SALE_AGES` in `household_member_candidates`.

- [ ] **Step 4: Run the domain tests and verify GREEN**

Run: `py -3.12 -m pytest -q -p no:cacheprovider tests/test_domain.py`

Expected: all domain tests pass.

---

### Task 2: Roll back a completed target transfer when payment fails

**Files:**
- Modify: `src/shady_sim_deals/orchestrator.py`
- Modify: `src/shady_sim_deals/processors.py`
- Test: `tests/test_transactions.py`
- Test: `tests/test_processors.py`

**Interfaces:**
- Consumes: `target_processor.process(transaction)`
- Produces: optional `target_processor.rollback(transaction)` called only after target processing and before terminal failure.
- Produces: `HouseholdMemberTargetProcessor.rollback(transaction)`.

- [ ] **Step 1: Write the failing orchestrator rollback test**

Use a funds fake whose `deposit` appends `payment` and raises `RuntimeError("deposit failed")`. Assert completion returns `False`, the event order contains `target`, `payment`, `rollback`, and the transaction ends in `failed` without `payment_completed`.

- [ ] **Step 2: Run the focused transaction test and verify RED**

Run: `py -3.12 -m pytest -q -p no:cacheprovider tests/test_transactions.py::test_payment_failure_rolls_back_processed_target`

Expected: FAIL because rollback is not called.

- [ ] **Step 3: Add the minimal rollback hook**

Track `target_processed = False` in `confirm_and_complete`. Set it after `process`. In the exception handler, when `target_processed` is true and payment is incomplete, call a callable `rollback` attribute if present. Preserve the original failure reason; if rollback itself fails, append `"; rollback failed: ..."`.

- [ ] **Step 4: Write the failing processor rollback test**

Extend the household fake with `rollback_transfer(sim_id)` and assert processor rollback calls it, unmarks the sold registry, and clears `transaction.outcome`.

- [ ] **Step 5: Implement processor rollback and verify GREEN**

```python
def rollback(self, transaction):
    self._households.rollback_transfer(transaction.target_id)
    self._sold.unmark_sold(transaction.target_id)
    transaction.outcome = None
```

Run: `py -3.12 -m pytest -q -p no:cacheprovider tests/test_transactions.py tests/test_processors.py`

Expected: all transaction and processor tests pass.

---

### Task 3: Implement current-patch Sims adapters with fake-game tests

**Files:**
- Modify: `src/shady_sim_deals/sims4_adapters.py`
- Create: `tests/test_sims4_adapters.py`

**Interfaces:**
- Produces: `age_key(sim_info) -> str`
- Produces: `Sims4TransactionValidator.validate(transaction) -> Optional[str]`
- Produces: `Sims4HouseholdAdapter.transfer_to_holding_household(sim_id) -> None`
- Produces: `Sims4HouseholdAdapter.rollback_transfer(sim_id) -> None`
- Produces: `Sims4HouseholdAdapter.is_transfer_complete(sim_id) -> bool`
- Holding household name: `ShadySimDeals Holdings`.

- [ ] **Step 1: Write failing pure age-conversion tests**

Use fake age enum values whose names are `TEEN`, `YOUNGADULT`, `ADULT`, and `ELDER`; assert conversion returns `teen`, `young_adult`, `adult`, and `elder`. Assert an unsupported age raises `ValueError`.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `py -3.12 -m pytest -q -p no:cacheprovider tests/test_sims4_adapters.py::test_age_key_maps_supported_game_ages`

Expected: FAIL because `age_key` does not exist.

- [ ] **Step 3: Implement `age_key` without importing game modules**

Normalize `getattr(age, "name", age)` by removing underscores and lowercasing, then map the four accepted spellings. Reject everything else.

- [ ] **Step 4: Write failing validation tests**

Inject fake service functions into `Sims4TransactionValidator` and cover missing actor, target outside the household, target equal to actor, unsupported age, missing funds, reserved target, and valid transaction.

- [ ] **Step 5: Implement validator dependency seams**

Accept optional `sim_info_lookup`, `household_lookup`, `reservation_check`, and `shutdown_check` callables. Default them lazily to EA services inside methods so host imports remain safe.

- [ ] **Step 6: Write failing holding-household transfer tests**

Create fake source/holding households and a fake manager. Assert:

- one hidden unplayed holding household is created and reused;
- the target is removed from source and added to holdings;
- membership is verified;
- a failed add restores source membership;
- `rollback_transfer` returns the target to the captured source.

- [ ] **Step 7: Implement transfer with compensation**

Create holdings with `household_manager.create_household(source.account, 0)`, set its name, call `set_to_hidden(0)`, remove the target with `destroy_if_empty_household=False`, then call `holdings.add_sim_info_to_household(sim_info)`. Store only the active transfer's source household ID in the adapter for rollback. Verify both sides after every move and raise `IntegrationUnavailable` on mismatch.

- [ ] **Step 8: Run adapter and existing tests**

Run: `py -3.12 -m pytest -q -p no:cacheprovider tests/test_sims4_adapters.py tests/test_processors.py tests/test_transactions.py`

Expected: all selected tests pass.

---

### Task 4: Wire the native phone picker and confirmation flow

**Files:**
- Modify: `src/shady_sim_deals/sims4_runtime.py`
- Modify: `src/shady_sim_deals/localization.py`
- Modify: `localization/en_us.json`
- Create: `tests/test_runtime.py`

**Interfaces:**
- Produces: `build_sale_candidate(sim_info) -> SaleCandidate`
- Produces: `PhoneSellHouseholdMemberInteraction` using `UiSimPicker`, `SimPickerRow`, and `UiDialogOkCancel` when game imports are available.
- Produces: one module-level `TransactionRegistry`, `SoldSimRegistry`, and `SimSalePricingService` for the loaded game session.

- [ ] **Step 1: Write the failing candidate-builder test**

Use a fake SimInfo with ID, first/last name, and supported age. Assert the resulting candidate has the mapped age and empty unverified modifier collections.

- [ ] **Step 2: Run the candidate test and verify RED**

Run: `py -3.12 -m pytest -q -p no:cacheprovider tests/test_runtime.py::test_build_sale_candidate_uses_verified_age_only`

Expected: FAIL because the builder does not exist.

- [ ] **Step 3: Implement candidate construction and shared services**

Build `SaleCandidate(sim_id, full_name, age_key, traits=(), skills=(), fame_level=0, occults=(), career_level=0, education="none")` and `BuyerContext(demand_multiplier=1.0, risk_multiplier=1.0)`.

- [ ] **Step 4: Write failing picker-row tests**

Test a pure helper that converts fake active-household SimInfo records to `SimRecord`, applies `household_member_candidates`, and returns eligible IDs. Cover actor exclusion and reservation/sold flags.

- [ ] **Step 5: Implement the picker helper and interaction callback**

The interaction's generator creates `UiSimPicker(owner=self.sim, resolver=self.get_resolver())`, adds one `SimPickerRow(sim_id=int(candidate_id))` per eligible Sim, and shows it with a response callback. A single selected ID proceeds; empty response cancels.

- [ ] **Step 6: Write failing confirmation-flow tests**

Use injected dialog and sale-service fakes. Assert cancellation performs no completion call, confirmation passes the selected ID once, and exceptions are logged and surfaced through the failure notification callback.

- [ ] **Step 7: Implement confirmation and completion**

Revalidate the selected target, calculate the offer, then show `UiDialogOkCancel`. On OK, create `SaleTransaction`, call `prepare`, then `confirm_and_complete`. Use existing localized titles/bodies with money and Sim tokens. Log picker open, selection, offer breakdown, cancellation, completion, and failure.

- [ ] **Step 8: Add localization keys**

Add English strings for `picker_title`, `picker_body`, `no_eligible_targets`, `lot51_missing`, and `holding_rollback_failed`, assigning sequential IDs after `0xA1100010` and mirroring them in `localization.py`.

- [ ] **Step 9: Run runtime and full host tests**

Run: `py -3.12 -m pytest -q -p no:cacheprovider tests`

Expected: all host tests pass.

---

### Task 5: Package the interaction, Lot51 injector, category, and English STBL

**Files:**
- Modify: `tuning/interactions/phone_sell_household_member.xml`
- Create: `tuning/categories/shady_sim_deals.xml`
- Create: `tuning/snippets/lot51_phone_injector.xml`
- Modify: `build_mod.py`
- Create: `tests/test_build.py`

**Interfaces:**
- Interaction instance: `0xEAA1200000000001`
- Category instance: `0xEAA1200000000010`
- Injector instance: `0xEAA1200000000020`
- ENG_US STBL instance: `0x00A1100000000001`, group `0x80000000`
- Resource types: interaction `0xE882D22F`, category `0x03E9D964`, snippet `0x7DF2169C`, STBL `0x220557DA`.

- [ ] **Step 1: Write failing STBL encoder tests**

Assert `build_stbl({0xA1100001: "ShadySimDeals"})` starts with `STBL`, encodes version 5, count 1, the 32-bit key, and UTF-8 text length/data according to the documented format.

- [ ] **Step 2: Run the focused build test and verify RED**

Run: `py -3.12 -m pytest -q -p no:cacheprovider tests/test_build.py::test_build_stbl_encodes_version_five_table`

Expected: FAIL because `build_stbl` does not exist.

- [ ] **Step 3: Implement the stdlib STBL encoder**

Use `struct.pack("<4sHBQ2sI", b"STBL", 5, 0, len(entries), b"\\0\\0", total_null_terminated_size)` and append each sorted entry as `struct.pack("<IBH", key, 0, len(text_bytes)) + text_bytes`.

- [ ] **Step 4: Generalize DBPF resources**

Replace the fixed interaction tuple with records containing `(path_or_bytes, type, group, instance)`. Preserve uncompressed payloads and the existing 96-byte DBPF header/index layout. Parse `localization/en_us.json` keys as hexadecimal integers and add the generated STBL resource.

- [ ] **Step 5: Write failing package-resource tests**

Build to a temporary output path and parse the DBPF index. Assert the exact interaction, category, snippet, and ENG_US STBL resource keys are present and the unborn/computer interaction keys are absent.

- [ ] **Step 6: Add the minimal interaction/category/injector tuning**

Use `PhoneSellHouseholdMemberInteraction` for the interaction and set its category reference to `0xEAA1200000000010`, `_saveable` disabled, and autonomy false.

Define the category with `m="interactions.pie_menu_category"`, `c="PieMenuCategory"`, localized name `0xA1100001`, and `collapse_if_only_one=False`.

Define the Lot51 snippet with `m="lot51_core.snippets.injector"`, `c="TuningInjector"`, `minimum_core_version=1.43`, `minimum_game_version=1.125.59`, and one `inject_by_object_tuning` entry targeting Sim object tuning `14965` whose `phone_affordances` list contains `0xEAA1200000000001`.

- [ ] **Step 7: Run package tests and build**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_build.py
py -3.12 build_mod.py
```

Expected: tests pass; build emits `dist/ShadySimDeals.ts4script` and `dist/ShadySimDeals.package` with no localization warning.

---

### Task 6: Update usage documentation and verify the release candidate

**Files:**
- Modify: `README.md`
- Modify: `DEVELOPMENT.md`
- Modify: `ARCHITECTURE.md`
- Modify: `install_mod.ps1`

**Interfaces:**
- Installation requires Lot51 Core 1.43+.
- Player-facing scope states phone-only and Teen–Elder targets.

- [ ] **Step 1: Update documentation**

Document the phone path, target restrictions, age-only live pricing, hidden holding household, uninstall warning, Lot51 dependency, patch 1.125.59.1030, disposable-save recommendation, and deferred features.

- [ ] **Step 2: Make installation fail fast on a running game**

Before building or copying, make `install_mod.ps1` stop with a clear message when `Get-Process TS4_x64 -ErrorAction SilentlyContinue` returns a process. Keep cache removal after successful copy.

- [ ] **Step 3: Run fresh verification**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests
py -3.12 build_mod.py
py -3.12 -m compileall -q src\shady_sim_deals
```

Expected: zero test failures, build exit code 0, and Python syntax compilation exit code 0.

- [ ] **Step 4: Inspect release contents**

List `.ts4script` ZIP entries and parse the package index with the test helper. Confirm only source runtime modules and the four planned package resources are present.

- [ ] **Step 5: Install after the game is closed**

Run `./install_mod.ps1`, restart the game, and inspect `shady_sim_deals.log`, `lot51_core.log`, and `lastException.txt` before opening the phone.

- [ ] **Step 6: Perform disposable-save smoke tests**

Verify phone visibility, picker filtering, cancel-without-change, one successful Teen–Elder sale, exact payment, target absence from the active household, and save/reload persistence in holdings.

If any live step fails, preserve logs and return to root-cause investigation before changing another variable.
