# Custom Phone App and Empty Picker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put Sell Household Member in a dedicated ShadySimDeals phone app and always open its picker, including when it has zero eligible rows.

**Architecture:** Keep Lot51 Core 1.43 as the phone-affordance injector. Package a custom PieMenuCategory XML plus its matching binary SimData client resource, then point the existing interaction at that category. Remove the zero-candidate early return and construct notifications through the game's tuned factory.

**Tech Stack:** Python 3.7-compatible Sims 4 script code, DBPF package resources, XML tuning, binary SimData, Lot51 Core 1.43, pytest on Python 3.12.

## Global Constraints

- Target The Sims 4 patch `1.125.59.1030`.
- Require Lot51 Core Library `1.43` or newer; do not redistribute it.
- Keep the live action limited to **Sell Household Member** and Teen-through-Elder human candidates.
- Reuse an existing EA phone icon; do not add an image asset.
- Never replace installed package or script files while `TS4_x64` is running.
- Preserve Python 3.7 syntax in `src/shady_sim_deals`.
- This workspace has no `.git` directory, so task checkpoints use fresh test output instead of commits.

## File Map

- Create `tuning/categories/shady_sim_deals_phone.xml`: simulation-side PieMenuCategory tuning.
- Modify `build_mod.py`: build the category SimData and package both category resources.
- Modify `tuning/interactions/phone_sell_household_member.xml`: reference the custom category.
- Modify `src/shady_sim_deals/sims4_runtime.py`: always open the picker and use a tuned notification factory.
- Modify `tests/test_build.py`: verify category IDs, groups, XML, SimData schema, and built package index.
- Modify `tests/test_runtime.py`: verify zero-row picker and notification construction.

---

### Task 1: Package the ShadySimDeals Phone Category

**Files:**
- Create: `tuning/categories/shady_sim_deals_phone.xml`
- Modify: `tuning/interactions/phone_sell_household_member.xml`
- Modify: `build_mod.py`
- Test: `tests/test_build.py`

**Interfaces:**
- Produces: `build_pie_menu_category_simdata(table_name: str, display_name_key: int, display_priority: int, icon_instance: int) -> bytes`.
- Produces: category tuning ID `0xEAA1200000000010` in XML group `0x80000000` and SimData group `0x00E9D967`.
- Consumed by: `package_resources()` and the interaction's `<T n="category">` reference.

- [ ] **Step 1: Replace the built-in category assertions with failing custom-category assertions**

Update `tests/test_build.py` so the planned resource keys include:

```python
CUSTOM_CATEGORY_ID = 0xEAA1200000000010

assert (0x03E9D964, 0x80000000, CUSTOM_CATEGORY_ID) in keys
assert (0x545AC67A, 0x00E9D967, CUSTOM_CATEGORY_ID) in keys
```

Replace `test_phone_interaction_uses_builtin_household_category` with:

```python
def test_phone_interaction_uses_matching_custom_category_resources():
    resources = build_mod.package_resources()
    interaction_data = next(data for data, kind, _, _ in resources if kind == 0xE882D22F)
    category_data = next(data for data, kind, _, _ in resources if kind == 0x03E9D964)
    simdata = next(data for data, kind, _, _ in resources if kind == 0x545AC67A)

    interaction = ET.fromstring(interaction_data)
    category = ET.fromstring(category_data)

    assert int(interaction.find("./T[@n='category']").text) == build_mod.CUSTOM_CATEGORY_ID
    assert int(category.attrib["s"]) == build_mod.CUSTOM_CATEGORY_ID
    assert category.find("./T[@n='_display_name']").text == "0xA1100001"
    assert simdata.startswith(b"DATA\x01\x01\x00\x00")
    assert b"PieMenuCategory\0" in simdata
    assert b"ShadySimDeals:phoneCategory\0" in simdata
```

- [ ] **Step 2: Run the focused build tests and confirm RED**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests\test_build.py
```

Expected: failures because category XML and SimData are absent and the interaction still references `105922`.

- [ ] **Step 3: Add the simulation-side category XML**

Create `tuning/categories/shady_sim_deals_phone.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<I c="PieMenuCategory" i="pie_menu_category" m="interactions.pie_menu_category" n="ShadySimDeals:phoneCategory" s="16906829660497641488">
  <T n="_collapsible">False</T>
  <T n="_display_name">0xA1100001</T>
  <T n="_display_priority">8</T>
  <T n="_icon" p="ShadySimDealsPhoneIcon">2f7d0004:00000000:6189ced9570b8609</T>
</I>
```

Change the interaction category to:

```xml
<T n="category">16906829660497641488</T>
```

- [ ] **Step 4: Add the minimum binary SimData writer and resources**

In `build_mod.py`, add constants:

```python
PIE_MENU_CATEGORY_TYPE = 0x03E9D964
SIMDATA_TYPE = 0x545AC67A
CUSTOM_CATEGORY_ID = 0xEAA1200000000010
CATEGORY_XML_GROUP = 0x80000000
CATEGORY_SIMDATA_GROUP = 0x00E9D967
```

Implement only the `DATA` v`0x101` shape required by `PieMenuCategory`. The generated table must contain one 56-byte row and one schema with hash `0x022065C1`:

```python
columns = (
    ("_collapsible", 0, 0),
    ("_display_name", 20, 4),
    ("_display_priority", 6, 8),
    ("_icon", 19, 16),
    ("_parent", 18, 32),
    ("_special_category", 8, 40),
    ("mood_overrides", 14, 48),
)
```

The single row values are:

```python
row = {
    "_collapsible": 0,
    "_display_name": 0xA1100001,
    "_display_priority": 8,
    "_icon": (0x6189CED9570B8609, 0x00B2D882, 0),
    "_parent": 0,
    "_special_category": 0,
    "mood_overrides": (-0x80000000, 0),
}
```

Use the game's case-insensitive 32-bit FNV-1 hash (lowercase UTF-8 bytes, multiply by `0x01000193`, then XOR each byte) for table, schema, and column names. Write every relative offset from the position of its own offset field; align the row table and trailing string area to 16 bytes. Keep this serializer in `build_mod.py` because it serves one resource shape and is not a general SimData library.

Add these resources to `package_resources()`:

```python
(
    (ROOT / "tuning" / "categories" / "shady_sim_deals_phone.xml").read_bytes(),
    PIE_MENU_CATEGORY_TYPE,
    CATEGORY_XML_GROUP,
    CUSTOM_CATEGORY_ID,
),
(
    build_pie_menu_category_simdata(
        "ShadySimDeals:phoneCategory", 0xA1100001, 8, 0x6189CED9570B8609
    ),
    SIMDATA_TYPE,
    CATEGORY_SIMDATA_GROUP,
    CUSTOM_CATEGORY_ID,
),
```

- [ ] **Step 5: Strengthen the test by parsing the SimData header**

In `tests/test_build.py`, add a small assertion helper that reads the `DATA` header and confirms version `0x101`, one table, one schema, the category table name, and schema hash `0x022065C1`. Do not duplicate a complete SimData decoder; offsets, counts, schema hash, and embedded names are the regression boundary.

- [ ] **Step 6: Run the focused build tests and confirm GREEN**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests\test_build.py
```

Expected: all build tests pass and the resource-key set contains five resources.

- [ ] **Step 7: Record the checkpoint**

Record the passing test count in the task notes. No commit is possible because this workspace has no `.git` directory.

---

### Task 2: Always Open the Picker and Correct Notification Construction

**Files:**
- Modify: `src/shady_sim_deals/sims4_runtime.py`
- Modify: `tests/test_runtime.py`

**Interfaces:**
- Consumes: `eligible_household_member_ids(...) -> tuple[str, ...]`.
- Produces: `PhoneSellHouseholdMemberInteraction._run_interaction_gen()` that calls `UiSimPicker.show_dialog()` for both empty and populated candidate tuples.
- Produces: `_show_notification(owner, resolver, title_key, text_key, *tokens)` using `UiDialogNotification.TunableFactory().default(...)`.

- [ ] **Step 1: Add a failing zero-row picker test**

Add fakes to `tests/test_runtime.py`:

```python
class FakePicker:
    last = None

    def __init__(self, owner, resolver):
        self.rows = []
        self.shown = False
        FakePicker.last = self

    def add_row(self, row):
        self.rows.append(row)

    def show_dialog(self, on_response):
        self.shown = True
        self.on_response = on_response
```

Monkeypatch `UiSimPicker`, `eligible_household_member_ids`, and `_runtime_services`, construct the interaction with a fake actor whose household contains only the actor, exhaust `_run_interaction_gen(None)`, then assert:

```python
assert FakePicker.last.shown is True
assert FakePicker.last.rows == []
assert FakePicker.last.min_selectable == 1
assert FakePicker.last.max_selectable == 1
```

- [ ] **Step 2: Add a failing tuned-notification test**

Use a fake `UiDialogNotification` whose `TunableFactory().default(...)` records its arguments and returns a fake dialog. Call `_show_notification(...)` and assert `default` received `owner` and `resolver`, the title/text callables were assigned, and `show_dialog()` was called.

- [ ] **Step 3: Run both focused tests and confirm RED**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests\test_runtime.py
```

Expected: the zero-candidate path calls the old failing notification instead of the picker, and direct notification construction bypasses `TunableFactory`.

- [ ] **Step 4: Remove the zero-candidate early return**

Delete only this branch from `PhoneSellHouseholdMemberInteraction._run_interaction_gen`:

```python
if not candidate_ids:
    _show_notification(...)
    return False
```

Keep `min_selectable = 1`, `max_selectable = 1`, and the existing row loop. With no rows, the picker opens but cannot submit a target.

- [ ] **Step 5: Construct notifications through tuned defaults**

Change `_show_notification` to:

```python
def _show_notification(owner, resolver, title_key, text_key, *tokens):
    dialog = UiDialogNotification.TunableFactory().default(
        owner=owner,
        resolver=resolver,
    )
    dialog.title = _dialog_text(title_key)
    dialog.text = _dialog_text(text_key, *tokens)
    dialog.show_dialog()
```

This supplies patch-required fields such as `tns_suppression_group` through the tuned factory.

- [ ] **Step 6: Run runtime and full host suites**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests\test_runtime.py
py -3.12 -m pytest -q -p no:cacheprovider
```

Expected: all tests pass with no regressions in filtering, pricing, transfer ordering, or rollback.

- [ ] **Step 7: Record the checkpoint**

Record the passing test counts in the task notes. No commit is possible because this workspace has no `.git` directory.

---

### Task 3: Build, Install, and Verify in Game

**Files:**
- Generated: `dist/ShadySimDeals.package`
- Generated: `dist/ShadySimDeals.ts4script`
- Installed after shutdown: `Documents/Electronic Arts/The Sims 4/Mods/ShadySimDeals/`

**Interfaces:**
- Consumes: the five resources returned by `package_resources()` and Python 3.7 bytecode from `src/shady_sim_deals`.
- Produces: installed artifacts loadable by patch `1.125.59.1030` with Lot51 Core `1.43`.

- [ ] **Step 1: Build fresh artifacts**

Run:

```powershell
py -3.12 build_mod.py
```

Expected: both files are rebuilt and the command exits `0`.

- [ ] **Step 2: Verify the package artifact before installation**

Parse the DBPF index as in `test_built_package_index_contains_every_planned_resource` and confirm these category keys exist:

```text
03E9D964:80000000:EAA1200000000010
545AC67A:00E9D967:EAA1200000000010
```

Also confirm the interaction resource contains category ID `16906829660497641488`.

- [ ] **Step 3: Stop at the game-process safety gate**

Run:

```powershell
Get-Process TS4_x64 -ErrorAction SilentlyContinue
```

If a process is returned, ask the user to save and close The Sims 4. Do not terminate it or install over loaded files.

- [ ] **Step 4: Install and clear the tuning cache after shutdown**

Run:

```powershell
.\install_mod.ps1
```

Expected: new package/script hashes match `dist`, and `localthumbcache.package` is removed.

- [ ] **Step 5: Verify the empty state in a disposable save**

Restart the game, load a one-Sim household, and verify:

1. The phone shows a **ShadySimDeals** app rather than placing the action in **Home**.
2. The app contains **Sell Household Member**.
3. Selecting it opens a zero-row picker that can be closed.
4. `shady_sim_deals.log` contains `picker_opened` with `candidate_count: 0`.
5. No new `lastUIException`, `lastException`, or `picker_failed` entry appears.

- [ ] **Step 6: Verify the populated state**

Use a disposable household with the actor plus one Teen-through-Elder human Sim. Confirm the picker shows only the second Sim, cancellation changes nothing, and confirmation transfers the target before depositing the displayed amount once.

- [ ] **Step 7: Record final evidence**

Record the full test count, artifact hashes, Lot51 injection log line, picker log lines for counts `0` and `1`, and whether any new exception report was generated.
