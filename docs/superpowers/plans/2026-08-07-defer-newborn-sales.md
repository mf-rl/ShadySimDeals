# Defer Newborn Sales Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Exclude newborns from the household-sale picker while preserving infant-through-elder and unborn sales.

**Architecture:** Reject normalized age `baby` in `eligible_household_member_ids()`, the single source of household picker rows. Keep the existing newborn adapter and packaged tuning dormant to avoid disturbing shared infant carry and rabbit-hole code.

**Tech Stack:** Python 3.7-compatible game script, pytest under Python 3.12, Sims 4 XML/DBPF build, PowerShell install script.

## Global Constraints

- Newborns must never appear in the household-member picker.
- Eligible infants and older Sims must remain unchanged.
- Unborn sales must remain unchanged.
- Keep the existing newborn adapter and packaged pickup tuning dormant.
- Do not add a feature flag, notification, dependency, pricing change, or unrelated refactor.
- Update maintained documentation and keep historical design/plan records intact.
- Commit and push to existing PR #7 without collaborator or AI attribution.

---

### Task 1: Exclude newborns at picker eligibility

**Files:**
- Modify: `tests/test_runtime.py:122-194`
- Modify: `src/shady_sim_deals/sims4_runtime.py:27-92`

**Interfaces:**
- Consumes: `age_key(sim_info) -> str` and existing `eligible_household_member_ids(sim_infos, actor_id, household_id, sold_check, reserved_check) -> tuple[str, ...]`.
- Produces: the same eligibility API, with normalized age `baby` omitted.

- [x] **Step 1: Change the shared eligibility regression first**

Keep `install_newborn_objects(monkeypatch, "baby")` so the fixture represents an
on-lot newborn that current production includes. Remove `"baby"` from the
expected tuple while retaining `"infant"` and every older eligible age:

```python
assert sims4_runtime.eligible_household_member_ids(
    sim_infos,
    actor_id="actor",
    household_id="home",
    sold_check=lambda sim_id: sim_id == "sold",
    reserved_check=lambda sim_id: sim_id == "reserved",
) == (
    "infant",
    "toddler",
    "child",
    "teen",
    "young-adult",
    "adult",
    "elder",
)
```

Delete the two obsolete tests that require on-lot newborn inclusion or distinguish
on-lot from off-lot newborns:

```python
test_eligible_household_member_ids_includes_uninstantiated_newborn
test_eligible_household_member_ids_excludes_off_lot_newborn
```

- [x] **Step 2: Run the regression and verify RED**

Run:

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests\test_runtime.py -k "eligible_household_member_ids_apply_shared_picker_rules"
```

Expected: FAIL because the actual tuple still begins with `"baby"`.

- [x] **Step 3: Add the minimum eligibility guard**

After age normalization, skip newborn records:

```python
try:
    age = age_key(sim_info)
except ValueError:
    continue
if age == "baby":
    continue
```

Since no household picker candidate now uses newborn object resolution, delete
`_is_newborn_on_active_lot()` and simplify record validity to:

```python
valid=_is_on_active_lot(sim_info)
and not getattr(sim_info, "is_dying", False)
and not getattr(sim_info, "is_destroyed", False),
```

Do not change `sims4_adapters.py`, `build_mod.py`, or newborn tuning resources.

- [x] **Step 4: Run focused and full tests**

Run:

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests\test_runtime.py -k "eligible_household_member_ids or unborn_candidates"
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider
```

Expected: focused eligibility tests pass; the complete suite passes with the
updated test count.

- [x] **Step 5: Commit the eligibility change**

```powershell
git add src/shady_sim_deals/sims4_runtime.py tests/test_runtime.py docs/superpowers/plans/2026-08-07-defer-newborn-sales.md
git commit -m "fix: exclude newborns from sale picker"
```

---

### Task 2: Align docs, review, build, push, and install

**Files:**
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`
- Modify: `DEVELOPMENT.md`
- Modify: `SPECS_CHECKLIST.md`
- Modify: `docs/superpowers/plans/2026-08-07-defer-newborn-sales.md`

**Interfaces:**
- Consumes: Task 1 household picker behavior.
- Produces: maintained documentation and an installed package that describe and enforce infant-through-elder eligibility.

- [ ] **Step 1: Align maintained documentation**

Make these exact semantic changes:

- `README.md`: supported household targets start at infant; remove the newborn pickup lifecycle; state newborn sales are deferred because native carry could not be made reliable.
- `ARCHITECTURE.md`: state the runtime rejects newborns before picker-row construction; note dormant newborn internals remain packaged but unreachable.
- `DEVELOPMENT.md`: describe infant-only pickup/handoff and change live checks from baby-through-elder to infant-through-elder.
- `SPECS_CHECKLIST.md`: replace newborn live acceptance with an explicit completed deferral/exclusion item; update picker filtering and rabbit-hole wording so unsupported newborns are not claimed as accepted behavior.

Do not rewrite historical specs or plans that record prior investigations.

- [ ] **Step 2: Review and verify**

Use `superpowers:requesting-code-review` over base
`4a75553ca6b6cf9b0ac19b55cfe7d13319c45322` through HEAD plus working docs.
Resolve every Critical or Important finding, then run:

```powershell
git diff --check 4a75553ca6b6cf9b0ac19b55cfe7d13319c45322
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider
py -3.12 build_mod.py
tar -tf dist\ShadySimDeals.ts4script
```

Expected: no diff errors, all tests pass, build succeeds, and the archive contains
`shady_sim_deals/sims4_runtime.pyc`.

- [ ] **Step 3: Commit and push PR #7**

```powershell
git add README.md ARCHITECTURE.md DEVELOPMENT.md SPECS_CHECKLIST.md docs/superpowers/plans/2026-08-07-defer-newborn-sales.md
git commit -m "docs: defer newborn sales"
git push
gh pr checks 7
git rev-parse HEAD
git rev-parse origin/fix/native-newborn-carry
git status --short
```

Expected: local and remote SHAs match, the worktree is clean, and GitHub reports
configured checks or explicitly reports none.

- [ ] **Step 4: Install only while the game is closed**

Confirm `TS4_x64.exe` is absent, then run:

```powershell
.\install_mod.ps1
```

Request a live picker check: newborn absent, infant present, and an infant sale
still completes normally.

---

## Plan Self-Review

- The eligibility test fails against current on-lot-newborn behavior before production changes.
- One guard at the picker boundary prevents all newborn household transactions.
- Infant and older candidates remain in the same regression tuple.
- Unborn eligibility is exercised in focused and full tests.
- Dormant newborn internals remain untouched as required.
- Maintained docs describe supported behavior; historical records remain intact.
