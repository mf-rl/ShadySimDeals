# Younger Household Sales Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add newborn/baby, infant, toddler, and child Sims to Sell Household Member on both phone and computer.

**Architecture:** Extend the existing shared age normalization and eligibility whitelist. Reuse the current SimInfo picker, pricing, validation, transaction, and holding-household transfer pipeline without adding device-specific or child-specific sale code.

**Tech Stack:** Python 3.7-compatible Sims 4 scripts, pytest on Python 3.12, DBPF packaging, Lot51 Core 1.43+

## Global Constraints

- Supported game patch is `1.125.59.1030`.
- Game-side Python must remain compatible with Python 3.7.
- Lot51 Core 1.43 or newer remains the only mod dependency.
- Support `BABY`, `INFANT`, `TODDLER`, `CHILD`, `TEEN`, `YOUNGADULT`, `ADULT`, and `ELDER`.
- Continue excluding the actor, pets, previously sold Sims, reserved Sims, and Sims outside the active household.
- Transfer SimInfo to the hidden holding household without hard deletion or explicit bassinet deletion.

---

### Task 1: Extend shared household-sale age support

**Files:**
- Modify: `src/shady_sim_deals/config.py:69-70`
- Modify: `src/shady_sim_deals/sims4_adapters.py:8-21`
- Test: `tests/test_sims4_adapters.py:88-112`
- Test: `tests/test_runtime.py:89-106`

**Interfaces:**
- Consumes: `age_key(sim_info) -> str`, `config.CHILD_AGES`, and `eligible_household_member_ids(...) -> tuple[str, ...]`.
- Produces: normalized keys for all eight supported ages and a whitelist containing the same eight keys.

- [ ] **Step 1: Write failing age-normalization and eligibility tests**

Replace the current supported-age assertions in `tests/test_sims4_adapters.py` with:

```python
@pytest.mark.parametrize(
    ("game_age", "expected"),
    (
        ("BABY", "baby"),
        ("INFANT", "infant"),
        ("TODDLER", "toddler"),
        ("CHILD", "child"),
        ("TEEN", "teen"),
        ("YOUNGADULT", "young_adult"),
        ("ADULT", "adult"),
        ("ELDER", "elder"),
    ),
)
def test_age_key_maps_supported_game_ages(game_age, expected):
    assert sims4_adapters.age_key(FakeSimInfo(game_age)) == expected
```

Change the unsupported-age test input from `CHILD` to `UNKNOWN`, and change the validator's unsupported-age case from `CHILD` to `UNKNOWN`.

In `tests/test_runtime.py`, include one eligible non-actor Sim for every supported age and assert their IDs are returned in household order:

```python
sim_infos = (
    FakeSimInfo("actor", age="ADULT"),
    FakeSimInfo("baby", age="BABY"),
    FakeSimInfo("infant", age="INFANT"),
    FakeSimInfo("toddler", age="TODDLER"),
    FakeSimInfo("child", age="CHILD"),
    FakeSimInfo("teen", age="TEEN"),
    FakeSimInfo("young-adult", age="YOUNGADULT"),
    FakeSimInfo("adult", age="ADULT"),
    FakeSimInfo("elder", age="ELDER"),
    FakeSimInfo("pet", age="ADULT", is_pet=True),
    FakeSimInfo("sold", age="ELDER"),
    FakeSimInfo("reserved", age="ADULT"),
    FakeSimInfo("elsewhere", age="ADULT", household_id="other"),
)
```

Expected result:

```python
(
    "baby",
    "infant",
    "toddler",
    "child",
    "teen",
    "young-adult",
    "adult",
    "elder",
)
```

- [ ] **Step 2: Run focused tests and verify the new cases fail**

Run:

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_sims4_adapters.py tests/test_runtime.py
```

Expected: failures for `BABY`, `INFANT`, `TODDLER`, and `CHILD` normalization and eligibility.

- [ ] **Step 3: Add the minimum shared implementation**

In `src/shady_sim_deals/config.py`, reuse the existing child-age set:

```python
HOUSEHOLD_SALE_AGES = CHILD_AGES | frozenset(
    ("teen", "young_adult", "adult", "elder")
)
```

In `src/shady_sim_deals/sims4_adapters.py`, add these entries to the existing map inside `age_key`:

```python
"BABY": "baby",
"INFANT": "infant",
"TODDLER": "toddler",
"CHILD": "child",
```

- [ ] **Step 4: Run focused and full tests**

Run:

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_sims4_adapters.py tests/test_runtime.py
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests
```

Expected: all tests pass.

- [ ] **Step 5: Commit the age support**

```powershell
git add src/shady_sim_deals/config.py src/shady_sim_deals/sims4_adapters.py tests/test_sims4_adapters.py tests/test_runtime.py
git commit -m "feat: support younger household sales"
```

### Task 2: Build and live-verify younger household sales

**Files:**
- Modify after verification: `SPECS_CHECKLIST.md:70-74`
- Generated: `dist/ShadySimDeals.package`
- Generated: `dist/ShadySimDeals.ts4script`

**Interfaces:**
- Consumes: the shared eight-age eligibility and transaction path from Task 1.
- Produces: installable artifacts and recorded acceptance evidence.

- [ ] **Step 1: Build the release artifacts**

Run:

```powershell
py -3.12 build_mod.py
```

Expected: both files appear in `dist/` and the build exits successfully.

- [ ] **Step 2: Install only after The Sims 4 is closed**

Run the repository's installation script after confirming the game process is no longer running:

```powershell
.\install_mod.ps1
```

Expected: the new `.package` and `.ts4script` replace the prior ShadySimDeals files in the game Mods folder.

- [ ] **Step 3: Perform the live acceptance check**

On phone or computer, verify the picker lists newborn/baby, infant, toddler, and child household members while excluding the actor. Complete at least one younger-Sim transaction and verify that payment occurs once, the target leaves the active household, and no genealogy data is hard-deleted. For a newborn, also note whether the game removes or leaves the empty bassinet.

- [ ] **Step 4: Record only verified checklist evidence**

After all four younger ages appear in the picker, mark `Baby, infant, toddler, and child support` complete in `SPECS_CHECKLIST.md`. Mark acceptance criterion 4 complete only when actor exclusion and all eight ages are confirmed.

- [ ] **Step 5: Commit the verified checklist**

```powershell
git add SPECS_CHECKLIST.md
git commit -m "docs: verify younger household sales"
```
