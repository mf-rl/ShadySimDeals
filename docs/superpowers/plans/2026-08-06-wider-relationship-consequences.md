# Wider Relationship Consequences Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply friendship losses to a sold household member's close relatives and the seller's remaining household members after a successful household-member sale.

**Architecture:** Extend the existing `Sims4SaleConsequences` post-success adapter with two injectable audience lookups. Resolve only the seller's current household and the target's immediate genealogy plus spouse, merge the IDs once, then apply one best-effort friendship delta per affected Sim.

**Tech Stack:** Python 3.7-compatible Sims 4 scripts, Python 3.12 and pytest, native `SimInfo`, `GenealogyTracker`, and `RelationshipTracker` APIs.

## Global Constraints

- Support The Sims 4 patch `1.125.59.1030` and Python 3.7 game bytecode.
- Household-only witnesses lose `25` friendship with the seller.
- Close relatives lose `50` friendship with the seller.
- A Sim in both groups receives only the stronger `-50` change.
- Keep the sold target's existing `-100` direct friendship change unchanged.
- Do not apply wider consequences to unborn-Nooboo sales.
- Do not scan every Sim in the save.
- Do not add tuning, dependencies, sentiments, observer buffs, or persistent grudges.
- Wider consequence failures never reverse a completed sale.
- Do not commit or push in this session.

## File Structure

- Modify `src/shady_sim_deals/sims4_adapters.py`: audience discovery, deduplication, friendship changes, and per-Sim failure isolation.
- Modify `tests/test_sims4_adapters.py`: deterministic host tests for audience rules, native lookup defaults, and failure continuation.
- Modify `README.md`: describe implemented witness and close-relative friendship effects.
- Modify `ARCHITECTURE.md`: document the bounded wider-audience pass.
- Modify `DEVELOPMENT.md`: record verified patch APIs and add live checks.
- Modify `SPECS_CHECKLIST.md`: split the broad pending item into implemented friendship effects and deferred sentiments/grudges.

---

### Task 1: Apply deduplicated wider friendship consequences

**Files:**
- Modify: `tests/test_sims4_adapters.py`
- Modify: `src/shady_sim_deals/sims4_adapters.py`

**Interfaces:**
- Extends: `Sims4SaleConsequences(..., household_member_lookup=None, close_relative_lookup=None)`.
- Produces: `Sims4SaleConsequences._apply_wider_relationships(transaction) -> None`.
- Live default: `_find_household_member_ids(actor_id) -> tuple[str, ...]` reads `SimInfo.household.sim_infos`.
- Live default: `_find_close_relative_ids(target_id) -> tuple[str, ...]` reads `GenealogyTracker.get_immediate_family_sim_ids_gen()` and `SimInfo.spouse_sim_id`.

- [x] **Step 1: Extend the test adapter seam**

Change `relationship_adapter` in `tests/test_sims4_adapters.py` to accept and pass the two audience lookups:

```python
def relationship_adapter(
    sims,
    selector=None,
    logger=None,
    household_member_lookup=None,
    close_relative_lookup=None,
):
    tunings = {
        0xEAA21FFB1081E014: "seller",
        0xEAA21FFB1081E015: "sold",
        0xEAA21FFB1081E016: "lost",
        0xEAA21FFB1081E017: "happy",
        0xEAA21FFB1081E018: "sad",
        0xEAA21FFB1081E019: "extreme_sad",
    }
    return sims4_adapters.Sims4SaleConsequences(
        sim_info_lookup=lambda sim_id: sims[sim_id],
        trait_lookup=lambda instance: tunings[instance],
        buff_lookup=lambda instance: tunings[instance],
        logger=logger,
        pregnant_reactions=selector,
        household_member_lookup=household_member_lookup or (lambda actor_id: ()),
        close_relative_lookup=close_relative_lookup or (lambda target_id: ()),
    )
```

- [x] **Step 2: Write the failing audience and deduplication test**

Add this test after the existing direct relationship tests:

```python
def test_wider_relationship_consequences_use_stronger_delta_once(
    all_hidden_reasons,
):
    sims = {
        "1": FakeConsequenceSimInfo(),
        "2": FakeConsequenceSimInfo(
            hidden=True, relationship_tracker=FakeRelationshipTracker()
        ),
        "3": FakeConsequenceSimInfo(
            relationship_tracker=FakeRelationshipTracker()
        ),
        "4": FakeConsequenceSimInfo(
            relationship_tracker=FakeRelationshipTracker()
        ),
    }
    adapter = relationship_adapter(
        sims,
        household_member_lookup=lambda actor_id: ("1", "2", "3", "4"),
        close_relative_lookup=lambda target_id: ("3",),
    )

    adapter.apply(SaleTransaction("household_member", "1", "2", "home"))

    assert sims["2"].relationship_tracker.changes == [(1, -100)]
    assert sims["3"].relationship_tracker.changes == [(1, -50)]
    assert sims["4"].relationship_tracker.changes == [(1, -25)]
```

This proves seller/target exclusion from the wider pass, relative precedence,
and one change per affected Sim.

- [x] **Step 3: Write failing unborn and failure-continuation tests**

```python
def test_unborn_sale_does_not_apply_wider_relationship_consequences(
    all_hidden_reasons,
):
    witness = FakeConsequenceSimInfo(
        relationship_tracker=FakeRelationshipTracker()
    )
    sims = {
        "1": FakeConsequenceSimInfo(),
        "2": FakeConsequenceSimInfo(
            relationship_tracker=FakeRelationshipTracker()
        ),
        "3": witness,
    }
    adapter = relationship_adapter(
        sims,
        selector=FakeReactionSelector("regretful"),
        household_member_lookup=lambda actor_id: ("3",),
        close_relative_lookup=lambda target_id: ("3",),
    )

    adapter.apply(SaleTransaction("unborn", "1", "2", "home"))

    assert witness.relationship_tracker.changes == []


def test_wider_relationship_failure_does_not_block_remaining_sims(
    all_hidden_reasons,
):
    logger = FakeConsequenceLogger()
    sims = {
        "1": FakeConsequenceSimInfo(),
        "2": FakeConsequenceSimInfo(
            hidden=True, relationship_tracker=FakeRelationshipTracker()
        ),
        "3": FakeConsequenceSimInfo(
            relationship_tracker=FakeRelationshipTracker(fail=True)
        ),
        "4": FakeConsequenceSimInfo(
            relationship_tracker=FakeRelationshipTracker()
        ),
    }
    adapter = relationship_adapter(
        sims,
        logger=logger,
        household_member_lookup=lambda actor_id: ("3", "4"),
    )

    adapter.apply(SaleTransaction("household_member", "1", "2", "home"))

    assert sims["4"].relationship_tracker.changes == [(1, -25)]
    assert logger.events[-1] == (
        "wider_relationship_consequence_failed",
        {
            "transaction_type": "household_member",
            "actor_id": "1",
            "target_id": "2",
            "affected_sim_id": "3",
            "source": "relationship",
        },
    )
```

Also prove the two discovery sources fail independently:

```python
def test_genealogy_lookup_failure_does_not_block_household_witnesses(
    all_hidden_reasons,
):
    logger = FakeConsequenceLogger()
    sims = {
        "1": FakeConsequenceSimInfo(),
        "2": FakeConsequenceSimInfo(
            hidden=True, relationship_tracker=FakeRelationshipTracker()
        ),
        "3": FakeConsequenceSimInfo(
            relationship_tracker=FakeRelationshipTracker()
        ),
    }
    adapter = relationship_adapter(
        sims,
        logger=logger,
        household_member_lookup=lambda actor_id: ("3",),
        close_relative_lookup=lambda target_id: (_ for _ in ()).throw(
            RuntimeError("genealogy unavailable")
        ),
    )

    adapter.apply(SaleTransaction("household_member", "1", "2", "home"))

    assert sims["3"].relationship_tracker.changes == [(1, -25)]
    assert logger.events[-1][0] == "wider_relationship_consequence_failed"
    assert logger.events[-1][1]["source"] == "genealogy"
```

- [x] **Step 4: Run the focused tests and verify RED**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_sims4_adapters.py -k "wider_relationship"
```

Expected: FAIL because `Sims4SaleConsequences.__init__` does not accept the two lookup arguments and no wider pass exists.

- [x] **Step 5: Implement the injected lookups and wider pass**

Extend `Sims4SaleConsequences.__init__`:

```python
def __init__(
    self,
    sim_info_lookup=None,
    trait_lookup=None,
    buff_lookup=None,
    logger=None,
    pregnant_reactions=None,
    household_member_lookup=None,
    close_relative_lookup=None,
):
    self._sim_info_lookup = (
        sim_info_lookup or Sims4TransactionValidator._find_sim_info
    )
    self._trait_lookup = trait_lookup or self._find_trait
    self._buff_lookup = buff_lookup or self._find_buff
    self._logger = logger or ModLogger()
    self._pregnant_reactions = (
        pregnant_reactions or PregnantSimReactionService(random)
    )
    self._household_member_lookup = (
        household_member_lookup or self._find_household_member_ids
    )
    self._close_relative_lookup = (
        close_relative_lookup or self._find_close_relative_ids
    )
```

Call `self._apply_wider_relationships(transaction)` after the existing direct
relationship try/except in `apply()`. Add:

```python
def _apply_wider_relationships(self, transaction):
    if transaction.transaction_type != "household_member":
        return
    actor_id = str(transaction.actor_id)
    target_id = str(transaction.target_id)
    deltas = {}
    try:
        for sim_id in self._household_member_lookup(actor_id):
            sim_id = str(sim_id)
            if sim_id not in (actor_id, target_id):
                deltas[sim_id] = -25
    except Exception:
        self._log_wider_failure(transaction, None, "household")
    try:
        for sim_id in self._close_relative_lookup(target_id):
            sim_id = str(sim_id)
            if sim_id not in (actor_id, target_id):
                deltas[sim_id] = -50
    except Exception:
        self._log_wider_failure(transaction, None, "genealogy")
    for sim_id, delta in deltas.items():
        try:
            sim_info = self._sim_info_lookup(sim_id)
            tracker = getattr(sim_info, "relationship_tracker", None)
            if tracker is None:
                raise IntegrationUnavailable(
                    "Relationship tracker is unavailable"
                )
            tracker.add_relationship_score(int(actor_id), delta)
        except Exception:
            self._log_wider_failure(transaction, sim_id, "relationship")

def _log_wider_failure(self, transaction, affected_sim_id, source):
    self._logger.exception(
        "wider_relationship_consequence_failed",
        transaction_type=transaction.transaction_type,
        actor_id=str(transaction.actor_id),
        target_id=str(transaction.target_id),
        affected_sim_id=(
            None if affected_sim_id is None else str(affected_sim_id)
        ),
        source=source,
    )
```

- [x] **Step 6: Implement the supported-patch default lookups**

Add these static methods to `Sims4SaleConsequences`:

```python
@staticmethod
def _find_household_member_ids(actor_id):
    actor = Sims4TransactionValidator._find_sim_info(str(actor_id))
    household = getattr(actor, "household", None)
    if household is None:
        raise IntegrationUnavailable("Actor household is unavailable")
    return tuple(str(sim_info.sim_id) for sim_info in household.sim_infos)

@staticmethod
def _find_close_relative_ids(target_id):
    target = Sims4TransactionValidator._find_sim_info(str(target_id))
    genealogy = getattr(target, "genealogy", None)
    if genealogy is None:
        raise IntegrationUnavailable("Target genealogy is unavailable")
    relative_ids = {
        str(sim_id)
        for sim_id in genealogy.get_immediate_family_sim_ids_gen()
    }
    spouse_id = int(getattr(target, "spouse_sim_id", 0) or 0)
    if spouse_id:
        relative_ids.add(str(spouse_id))
    return tuple(sorted(relative_ids))
```

`get_immediate_family_sim_ids_gen()` covers parents, children, and siblings on
patch `1.125.59.1030`; `spouse_sim_id` supplies the spouse separately.

- [x] **Step 7: Test the default native lookup boundaries**

Add:

```python
def test_wider_relationship_default_lookups_use_household_and_genealogy(
    monkeypatch,
):
    household = type(
        "Household",
        (),
        {"sim_infos": (type("Member", (), {"sim_id": 3})(),)},
    )()
    genealogy = type(
        "Genealogy",
        (),
        {"get_immediate_family_sim_ids_gen": lambda self: iter((4, 5, 6))},
    )()
    sims = {
        "1": type("Actor", (), {"household": household})(),
        "2": type(
            "Target",
            (),
            {"genealogy": genealogy, "spouse_sim_id": 7},
        )(),
    }
    monkeypatch.setattr(
        sims4_adapters.Sims4TransactionValidator,
        "_find_sim_info",
        staticmethod(lambda sim_id: sims[sim_id]),
    )

    assert sims4_adapters.Sims4SaleConsequences._find_household_member_ids(
        "1"
    ) == ("3",)
    assert set(
        sims4_adapters.Sims4SaleConsequences._find_close_relative_ids("2")
    ) == {"4", "5", "6", "7"}
```

- [x] **Step 8: Run adapter and full tests**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_sims4_adapters.py
py -3.12 -m pytest -q -p no:cacheprovider tests
```

Expected: all tests PASS; the existing target `-100`, unborn
`+10/-25/-75`, self-target neutrality, traits, and moodlets remain unchanged.

- [x] **Step 9: Leave the implementation uncommitted**

Run:

```powershell
git diff --check
git status --short
```

Expected: only the approved source, test, design, and plan changes are listed;
do not run `git add`, `git commit`, or `git push`.

---

### Task 2: Align maintained documentation and verify the build

**Files:**
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`
- Modify: `DEVELOPMENT.md`
- Modify: `SPECS_CHECKLIST.md`
- Verify: `dist/ShadySimDeals.ts4script`
- Verify: `dist/ShadySimDeals.package`

**Interfaces:**
- Consumes: Task 1 friendship behavior.
- Produces: accurate current scope, live-test guidance, and checklist status.

- [x] **Step 1: Update the maintained behavior descriptions**

Make these exact documentation changes:

- `README.md`: after the direct relationship paragraph, state that parents,
  children, siblings, and spouses of a sold household member lose `50`
  friendship with the seller, while other remaining household members lose
  `25`; overlapping Sims receive only `-50`.
- `ARCHITECTURE.md`: describe the deduplicated current-household plus immediate-
  genealogy pass in `Sims4SaleConsequences` and its per-Sim failure isolation.
- `DEVELOPMENT.md`: record `GenealogyTracker.get_immediate_family_sim_ids_gen()`,
  `SimInfo.spouse_sim_id`, and `SimInfo.household.sim_infos` as verified patch
  surfaces; add a live check for relative/witness deltas and overlap deduping.
- `SPECS_CHECKLIST.md`: replace the broad unchecked relationship item with a
  checked friendship-only item and an unchecked item for observer buffs,
  sentiments, and persistent grudges.

- [x] **Step 2: Run documentation consistency checks**

Run:

```powershell
rg -n "relative|witness|sentiment|grudge|friendship|genealogy" README.md ARCHITECTURE.md DEVELOPMENT.md SPECS_CHECKLIST.md
git diff --check
```

Expected: all four maintained documents agree on `-100` for the target, `-50`
for close relatives, `-25` for household-only witnesses, and deferred
sentiments/grudges; the whitespace check is silent.

- [x] **Step 3: Run final automated verification and build**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests
py -3.12 build_mod.py
git diff --check
git status --short
```

Expected: the full suite passes, both distribution artifacts build, whitespace
checks are clean, and all source/documentation changes remain uncommitted.

- [x] **Step 4: Record the live verification boundary**

Leave any new live-verification subitem unchecked. On patch `1.125.59.1030`, a
later live session must sell a Sim with one household-only witness and one close
relative who is also in the household, then confirm `-25` and one `-50`
respectively without a new `lastException.txt`.
