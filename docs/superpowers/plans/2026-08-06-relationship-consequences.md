# Direct Relationship Consequences Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply direct friendship changes after successful household-member and other-target unborn sales.

**Architecture:** Extend the existing `Sims4SaleConsequences` post-success adapter. Keep trait/moodlet and relationship failures independent, use the verified `RelationshipTracker` API, and inject the existing pregnant-reaction selector for deterministic tests.

**Tech Stack:** Python 3.7-compatible Sims 4 scripts, Python 3.12 and pytest, native Sims 4 `RelationshipTracker` APIs.

## Global Constraints

- Support The Sims 4 patch `1.125.59.1030` and Python 3.7 game bytecode.
- Add no dependency, tuning resource, sentiment, relationship bit, or new transaction state.
- Change only the relationship between the seller and direct target.
- Never reverse a completed sale because a relationship consequence failed.
- Do not commit or push in this session.

---

### Task 1: Add direct relationship consequences

**Files:**
- Modify: `tests/test_sims4_adapters.py`
- Modify: `src/shady_sim_deals/sims4_adapters.py`

**Interfaces:**
- Consumes: `PregnantSimReactionService.select(relationship_score) -> str`.
- Consumes: `SimInfo.relationship_tracker.get_relationship_score(other_sim_id)` and `add_relationship_score(other_sim_id, increment)`.
- Extends: `Sims4SaleConsequences(..., pregnant_reactions=None)`.

- [x] **Step 1: Write failing adapter tests**

Add a fake relationship tracker that records score reads and increments. Test:

```python
def test_household_sale_subtracts_one_hundred_friendship():
    consequences.apply(SaleTransaction("household_member", "1", "2", "home"))
    assert target.relationship_tracker.changes == [(1, -100)]


@pytest.mark.parametrize(
    ("outcome", "delta"),
    (("complicit", 10), ("regretful", -25), ("betrayed", -75)),
)
def test_other_target_unborn_sale_applies_selected_relationship_delta(outcome, delta):
    selector = SimpleNamespace(select=lambda score: outcome)
    consequences = Sims4SaleConsequences(
        sim_info_lookup=lookup,
        trait_lookup=trait_lookup,
        buff_lookup=buff_lookup,
        pregnant_reactions=selector,
    )
    consequences.apply(SaleTransaction("unborn", "1", "2", "home"))
    assert target.relationship_tracker.reads == [1]
    assert target.relationship_tracker.changes == [(1, delta)]
```

Also test self-target unborn neutrality and a broken tracker logging
`relationship_consequence_failed` without raising.

- [x] **Step 2: Run tests and verify RED**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_sims4_adapters.py -k relationship_consequence
```

Expected: FAIL because `pregnant_reactions` and relationship mutation do not exist.

- [x] **Step 3: Implement the minimum adapter behavior**

In `sims4_adapters.py`, import `random` and `PregnantSimReactionService`. Add:

```python
RELATIONSHIP_DELTAS = {
    "complicit": 10,
    "regretful": -25,
    "betrayed": -75,
}
```

Accept `pregnant_reactions=None` and default it to
`PregnantSimReactionService(random)`. Split `apply()` into two independent
best-effort calls: preserve the existing trait/moodlet logic and add
`_apply_relationship(transaction)`. That method returns for self-target or
unknown transaction types, uses `-100` for household sales, and otherwise
selects the unborn delta from the target's current relationship score. On
failure, log `relationship_consequence_failed` with transaction type and IDs.

- [x] **Step 4: Run focused and full tests**

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_sims4_adapters.py
py -3.12 -m pytest -q -p no:cacheprovider tests
```

Expected: all tests pass and existing trait/moodlet failure behavior remains unchanged.

---

### Task 2: Align maintained documentation

**Files:**
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`
- Modify: `DEVELOPMENT.md`
- Modify: `SPECS_CHECKLIST.md`

**Interfaces:**
- Consumes: Task 1 behavior.
- Produces: current scope and deferred-work documentation.

- [x] **Step 1: Update current behavior and status**

Document the `-100` household friendship change and the `+10/-25/-75` unborn
outcomes. Mark `Relationship consequences` complete. Remove relationship
consequences from the release omission list, and state that relatives,
witnesses, sentiments, and grudges remain deferred.

- [x] **Step 2: Verify documentation consistency**

```powershell
rg -n "relationship|friendship|sentiment|grudge|witness" README.md ARCHITECTURE.md DEVELOPMENT.md SPECS_CHECKLIST.md
git diff --check
```

Expected: maintained documents agree on implemented direct-participant effects and deferred wider consequences.

---

### Task 3: Verify the deliverable

**Files:**
- Verify: `src/shady_sim_deals/sims4_adapters.py`
- Verify: `dist/ShadySimDeals.ts4script`
- Verify: `dist/ShadySimDeals.package`

- [x] **Step 1: Run full automated verification and build**

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests
py -3.12 build_mod.py
git diff --check
git status --short
```

Expected: the full suite passes, both artifacts build, the diff has no whitespace errors, and all changes remain uncommitted.
