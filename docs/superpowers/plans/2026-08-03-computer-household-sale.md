# Computer Household Sale Implementation Plan

> **Historical note (2026-08-07):** This implementation plan is retained as a development record. Its unchecked boxes describe the original workflow, not current repository status; use [`SPECS_CHECKLIST.md`](../../../SPECS_CHECKLIST.md) for current status.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the existing household-member sale workflow to compatible computers and add a repository-wide `SPECS.md` completion checklist.

**Architecture:** A shared interaction base owns the native picker, offer, confirmation, transfer, payment, and notification flow. Thin phone and computer subclasses identify the entry point, while Lot51 Core injects the computer affordance by the `Func_Computer` object tag.

**Tech Stack:** Python 3.7-compatible game scripts, Python 3.12 and pytest for tests, Sims 4 XML tuning, DBPF packaging, Lot51 Core 1.43.

## Global Constraints

- Support The Sims 4 patch `1.125.59.1030`.
- Require Lot51 Core Library `1.43` or newer.
- Do not duplicate filtering, pricing, transaction, or consequence logic between phone and computer.
- Use native Sims 4 dialogs and pickers; do not add custom Scaleform UI.
- Do not package either unborn-Nooboo interaction in this release.
- Do not claim computer animation, rabbit-hole behavior, or in-game visibility until each is verified in game.

---

### Task 1: Share the household-sale interaction flow

**Files:**
- Modify: `tests/test_runtime.py`
- Modify: `src/shady_sim_deals/sims4_runtime.py`

**Interfaces:**
- Consumes: `eligible_household_member_ids(...)`, `complete_household_sale(...)`, and `_runtime_services()`.
- Produces: `_HouseholdMemberSaleInteraction`, `PhoneSellHouseholdMemberInteraction`, and `ComputerSellHouseholdMemberInteraction`.

- [ ] **Step 1: Write the failing parity tests**

Add tests proving both public entry classes inherit one implementation and the
computer entry opens the same picker:

```python
def test_phone_and_computer_household_sales_share_one_implementation():
    shared = sims4_runtime._HouseholdMemberSaleInteraction

    assert issubclass(sims4_runtime.PhoneSellHouseholdMemberInteraction, shared)
    assert issubclass(sims4_runtime.ComputerSellHouseholdMemberInteraction, shared)
    assert "_run_interaction_gen" not in sims4_runtime.PhoneSellHouseholdMemberInteraction.__dict__
    assert "_run_interaction_gen" not in sims4_runtime.ComputerSellHouseholdMemberInteraction.__dict__


def test_computer_household_sale_opens_shared_picker(monkeypatch):
    actor_info = FakeSimInfo(sim_id=42)
    actor = type(
        "Actor",
        (),
        {
            "sim_id": 42,
            "household": type(
                "Household", (), {"id": "home", "sim_infos": (actor_info,)}
            )(),
        },
    )()
    never = type(
        "Never",
        (),
        {
            "is_sold": lambda self, sim_id: False,
            "is_reserved": lambda self, sim_id: False,
        },
    )()
    monkeypatch.setattr(sims4_runtime, "UiSimPicker", FakePicker)
    monkeypatch.setattr(
        sims4_runtime,
        "_runtime_services",
        lambda: {"sold": never, "reservations": never},
    )
    interaction = object.__new__(
        sims4_runtime.ComputerSellHouseholdMemberInteraction
    )
    interaction.sim = actor
    interaction.get_resolver = lambda: "resolver"

    list(interaction._run_interaction_gen(None))

    assert FakePicker.last.shown is True
    assert FakePicker.last.rows == []
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_runtime.py
```

Expected: FAIL because `_HouseholdMemberSaleInteraction` does not exist and the
computer class still inherits the unavailable-integration implementation.

- [ ] **Step 3: Move the existing flow to the shared class**

Rename the current behavior-owning phone class and add two thin entry classes:

```python
class _HouseholdMemberSaleInteraction(_ShadySimDealsInteraction):
    transaction_type = "household_member"
    string_key = "sell_household_member"

    # Keep the existing _run_interaction_gen, _on_picker_response, and
    # _complete_sale methods here unchanged.


class PhoneSellHouseholdMemberInteraction(_HouseholdMemberSaleInteraction):
    entry_point = "phone"


class ComputerSellHouseholdMemberInteraction(_HouseholdMemberSaleInteraction):
    entry_point = "computer"
```

Remove the old empty `ComputerSellHouseholdMemberInteraction` declaration. Do
not modify the unborn interaction classes.

- [ ] **Step 4: Run the focused and full suites**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_runtime.py
py -3.12 -m pytest -q -p no:cacheprovider tests
```

Expected: both commands PASS.

- [ ] **Step 5: Commit the shared runtime flow**

```powershell
git add src/shady_sim_deals/sims4_runtime.py tests/test_runtime.py
git commit -m "refactor: share household sale entry flow"
```

---

### Task 2: Inject and package the computer interaction

**Files:**
- Modify: `tests/test_build.py`
- Modify: `tuning/interactions/computer_sell_household_member.xml`
- Modify: `tuning/snippets/lot51_phone_injector.xml`
- Modify: `build_mod.py`

**Interfaces:**
- Consumes: Lot51 `TuningInjector.inject_by_object_tags`, `tags`, and `affordances` tunables.
- Produces: interaction resource `0xEAA21FFB1081E003`, injected into objects tagged `Func_Computer`.

- [ ] **Step 1: Replace the phone-only package test with exact parity assertions**

Update the resource-key test to expect six resources:

```python
def test_package_resources_include_phone_and_computer_household_sales():
    resources = build_mod.package_resources()
    keys = {
        (resource_type, group, instance)
        for _, resource_type, group, instance in resources
    }

    assert keys == {
        (0xE882D22F, 0, 0xEAA1200000000001),
        (0xE882D22F, 0, 0xEAA21FFB1081E003),
        (0x03E9D964, 0x80000000, 0xEAA1200000000010),
        (0x545AC67A, 0x00E9D967, 0xEAA1200000000010),
        (0x7DF2169C, 0, 0xEAA1200000000020),
        (0x220557DA, 0x80000000, 0x00A1100000000001),
    }
```

Add an injector linkage test:

```python
def test_lot51_injector_targets_computers_with_computer_interaction():
    injector_data = next(
        data
        for data, resource_type, _, _ in build_mod.package_resources()
        if resource_type == build_mod.SNIPPET_TYPE
    )
    injector = ET.fromstring(injector_data)
    computer_entry = injector.find("./L[@n='inject_by_object_tags']/U")

    assert computer_entry.find("./L[@n='tags']/E").text == "Func_Computer"
    assert int(computer_entry.find("./L[@n='affordances']/T").text) == int(
        "EAA21FFB1081E003", 16
    )
```

Retain the existing phone/category assertions and update the DBPF-index expected
set to the same six keys.

- [ ] **Step 2: Run the build tests and verify RED**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_build.py
```

Expected: FAIL because the computer resource and tag injection are absent.

- [ ] **Step 3: Tune the computer interaction**

Keep its existing ID and class, then assign the shared ShadySimDeals category:

```xml
<?xml version="1.0" encoding="utf-8"?>
<I c="ComputerSellHouseholdMemberInteraction" i="interaction" m="shady_sim_deals.sims4_runtime" n="ShadySimDeals:ComputerSellHouseholdMember" s="16907111114276462595">
  <V n="_saveable" t="disabled" />
  <T n="allow_autonomous">False</T>
  <T n="category">16906829660497641488</T>
</I>
```

- [ ] **Step 4: Extend the Lot51 injector**

Keep the existing phone entry and add:

```xml
  <L n="inject_by_object_tags">
    <U>
      <L n="tags">
        <E>Func_Computer</E>
      </L>
      <L n="affordances">
        <T>16907111114276462595</T>
      </L>
    </U>
  </L>
```

Lot51 1.43 exposes these exact tunables in
`TuningInjector`/`TunableObjectInjectionByTags`; `affordances` writes to the
computer object's normal super-affordance list.

- [ ] **Step 5: Add the computer XML to `package_resources()`**

Add this tuple immediately after the phone interaction tuple:

```python
        (
            (
                ROOT
                / "tuning"
                / "interactions"
                / "computer_sell_household_member.xml"
            ).read_bytes(),
            INTERACTION_TUNING_TYPE,
            0,
            0xEAA21FFB1081E003,
        ),
```

- [ ] **Step 6: Run build tests and the full suite**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_build.py
py -3.12 -m pytest -q -p no:cacheprovider tests
```

Expected: both commands PASS, and neither unborn interaction is in the expected
resource set.

- [ ] **Step 7: Commit the computer packaging**

```powershell
git add build_mod.py tests/test_build.py tuning/interactions/computer_sell_household_member.xml tuning/snippets/lot51_phone_injector.xml
git commit -m "feat: add household sales to computers"
```

---

### Task 3: Add the `SPECS.md` implementation checklist

**Files:**
- Create: `SPECS_CHECKLIST.md`
- Modify: `README.md`
- Modify: `DEVELOPMENT.md`

**Interfaces:**
- Consumes: `SPECS.md`, current automated tests, and confirmed phone gameplay results.
- Produces: a maintained status checklist; no runtime interface.

- [ ] **Step 1: Create the checklist with evidence-based state**

Create `SPECS_CHECKLIST.md` with this structure and state after Tasks 1–2:

```markdown
# ShadySimDeals Specification Checklist

This checklist tracks `SPECS.md`. Checked items are supported by repository code,
automated tests, or recorded in-game verification. Items requiring new game-side
verification remain unchecked.

## Implementation phases

### Phase 1: Core

- [x] Repository analysis and project skeleton
- [x] Logging and configuration
- [x] Shared transaction models and state machine
- [x] Pricing service and unit tests

### Phase 2: Entry points and dialogs

- [x] Phone household-sale injection
- [x] Computer household-sale injection packaged and unit-tested
- [ ] Computer household-sale visibility verified in game
- [x] Shared native household picker and confirmation dialog
- [ ] Phone and computer unborn-Nooboo entry points
- [ ] Computer-use and phone-use animations

### Phase 3: Household-member transaction

- [ ] Real rabbit-hole workflow and timed return
- [x] Safe household transfer with rollback
- [x] Exactly-once payment ordering
- [ ] Seller buffs
- [ ] Relationship consequences

### Phase 4: Unborn-Nooboo transaction

- [ ] Pregnant-Sim picker
- [ ] Verified pregnancy adapter and safe pregnancy conclusion
- [ ] Unborn rabbit hole
- [ ] Multiple-offspring pricing connected to game pregnancy data
- [ ] Pregnant-Sim reaction

### Phase 5: Sold-Sim outcomes

- [x] Hidden ShadySimDeals Holdings household
- [x] Session-local sold-Sim registry
- [ ] Save-slot-aware sold-Sim registry
- [ ] Ghost-return outcome
- [ ] Delayed events

### Phase 6: Release readiness

- [x] `.package` and `.ts4script` build
- [x] English localization resources
- [x] Architecture, build, installation, and usage documentation
- [x] Automated regression suite
- [ ] Computer interaction live compatibility check
- [ ] Full acceptance regression in the supported game patch

## Acceptance criteria

- [x] 1. ShadySimDeals appears on supported phones.
- [ ] 2. ShadySimDeals appears on supported computers.
- [ ] 3. Both entry points expose household-member and unborn-Nooboo sales.
- [ ] 4. Household picker supports every required age and excludes the actor.
  - [x] Actor exclusion and Teen-through-Elder filtering
  - [ ] Baby, infant, toddler, and child support
- [ ] 5. Unborn picker includes only pregnant household members, including the actor.
- [x] 6. A calculated offer appears before confirmation.
- [x] 7. Cancellation makes no changes.
- [ ] 8. Confirmation starts the appropriate rabbit hole.
- [ ] 9. Household-member transactions return only the seller from a rabbit hole.
- [x] 10. Targets move out of the active household without hard deletion.
- [x] 11. Payment is deposited exactly once and only after target processing.
- [ ] 12. Unborn transactions safely conclude the selected pregnancy.
- [ ] 13. Twins and triplets affect the live pregnancy offer.
- [ ] 14. Sellers receive trait-appropriate buffs.
- [ ] 15. Other selected pregnant Sims receive reaction buffs.
- [x] 16. Transactions validate and fail safely, including transfer rollback.
- [x] 17. Pricing and transaction logic have automated tests.
- [x] 18. The mod builds installable `.package` and `.ts4script` files.
- [x] 19. Current user-facing text uses localization resources.
- [x] 20. Build, installation, architecture, and usage documentation exists.
```

- [ ] **Step 2: Update user and developer documentation**

In `README.md`:

- Change the first-release description to say household sales are available on
  phones and compatible computers.
- Add computer usage: click a computer, open **ShadySimDeals**, then choose
  **Sell Household Member**.
- Remove computer actions from the omitted-feature list.
- Link to `SPECS_CHECKLIST.md` for implementation status.

In `DEVELOPMENT.md`:

- Record that Lot51 `inject_by_object_tags` targets `Func_Computer` through the
  normal `affordances` list.
- Add a live check for the ShadySimDeals computer category and sale action.
- Keep computer animation listed as deferred.

- [ ] **Step 3: Verify checklist accuracy and Markdown integrity**

Run:

```powershell
rg -n "^- \[[ x]\]" SPECS_CHECKLIST.md
rg -n "computer|Computer" README.md DEVELOPMENT.md SPECS_CHECKLIST.md
git diff --check
```

Expected: all six phases and twenty numbered acceptance criteria are present;
no unchecked behavior is described as completed.

- [ ] **Step 4: Commit the status documentation**

```powershell
git add SPECS_CHECKLIST.md README.md DEVELOPMENT.md
git commit -m "docs: track specification implementation status"
```

---

### Task 4: Build and hand off the game verification

**Files:**
- Verify: `dist/ShadySimDeals.package`
- Verify: `dist/ShadySimDeals.ts4script`
- Modify after live confirmation only: `SPECS_CHECKLIST.md`

**Interfaces:**
- Consumes: all completed runtime, tuning, packaging, and documentation changes.
- Produces: rebuilt distributables and a precise live-test handoff.

- [ ] **Step 1: Run the final automated verification**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests
py -3.12 build_mod.py
```

Expected: the full suite passes and both files are rebuilt in `dist/`.

- [ ] **Step 2: Inspect the artifacts**

Run:

```powershell
Get-Item dist/ShadySimDeals.package,dist/ShadySimDeals.ts4script | Select-Object Name,Length,LastWriteTime
```

Expected: both files exist, are non-empty, and have the current build timestamp.

- [ ] **Step 3: Install only while the game is closed**

Run:

```powershell
.\install_mod.ps1
```

Do not run this step if The Sims 4 is open. The package contains tuning and must
be loaded from a clean game start.

- [ ] **Step 4: Perform the live computer smoke test**

1. Start the supported game patch with Lot51 Core 1.43 or newer.
2. Load a household containing an eligible Teen-through-Elder target.
3. Click a compatible computer and verify **ShadySimDeals** appears.
4. Choose **Sell Household Member** and verify the native picker opens.
5. Cancel once and confirm no funds or household membership changes.
6. Repeat, confirm a sale, and verify one payment plus target transfer.
7. Check `lastException.txt`, `ShadySimDeals.log`, and `lot51_core.log`.

- [ ] **Step 5: Record live confirmation**

Only after Step 4 succeeds, change these checklist items to checked:

```markdown
- [x] Computer household-sale visibility verified in game
- [x] Computer interaction live compatibility check
- [x] 2. ShadySimDeals appears on supported computers.
```

Commit that evidence:

```powershell
git add SPECS_CHECKLIST.md
git commit -m "docs: confirm computer interaction in game"
```

If the live test fails, leave the boxes unchecked and capture the exact exception
or log entry before changing code.
