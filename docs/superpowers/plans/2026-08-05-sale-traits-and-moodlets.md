# Sale Traits and Moodlets Implementation Plan

> **Historical note (2026-08-07):** This plan records the original implementation. Its base-game trait and buff icon references are superseded by the custom DST5 icon system documented in [`2026-08-06-custom-icons-design.md`](../specs/2026-08-06-custom-icons-design.md) and the automatic source-PNG compilation pipeline documented in [`2026-08-07-automatic-icon-compilation-design.md`](../specs/2026-08-07-automatic-icon-compilation-design.md).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the live process-local sold marker with a save-managed visible trait and apply the approved permanent traits and timed moodlets after successful sales.

**Architecture:** Keep the existing domain registry and orchestrator contracts. Add Sims 4-backed registry and consequence adapters in `sims4_adapters.py`, then inject them once from `_runtime_services()` so phone and computer sales share identical behavior. Package three trait and three buff XML resources through the existing DBPF builder.

**Tech Stack:** Python 3.7-compatible Sims 4 scripts, XML instance tuning, DBPF/STBL packaging, pytest on Python 3.12.

## Global Constraints

- Traits are permanent, visible, non-CAS-selectable `GAMEPLAY` traits and consume no personality slot.
- Resource IDs are `0xEAA21FFB1081E014`–`0xEAA21FFB1081E019` in trait-then-buff order.
- Localization keys are `0xA1100018`–`0xA1100023` in name/description pairs.
- Seller moodlet: `+4 Happy` for 12 Sim hours (720 Sim minutes).
- Sold moodlet: `+6 Sad` for 24 Sim hours (1440 Sim minutes).
- Lost-unborn moodlet: `+10 Sad` for 48 Sim hours (2880 Sim minutes).
- Failed, cancelled, and rolled-back sales leave no new consequences.
- Exiting without saving relies exclusively on normal `SimInfo` save rollback; do not add main-menu hooks.
- Do not add dependencies or duplicate behavior between phone and computer interactions.

---

## File Structure

- Create `tuning/traits/family_asset_liquidator.xml`: visible seller trait.
- Create `tuning/traits/outsourced_by_my_own_family.xml`: visible authoritative sold marker.
- Create `tuning/traits/stork_claim_mysteriously_denied.xml`: visible lost-unborn trait.
- Create `tuning/buffs/quarterly_profits_fewer_mouths.xml`: Happy +4/720 moodlet.
- Create `tuning/buffs/love_had_a_return_policy.xml`: Sad +6/1440 moodlet.
- Create `tuning/buffs/nursery_has_been_downsized.xml`: Sad +10/2880 moodlet.
- Modify `localization/en_us.json`: approved names and descriptions.
- Modify `build_mod.py`: trait/buff resource types and six package entries.
- Modify `src/shady_sim_deals/sims4_adapters.py`: game-backed sold registry and shared consequence adapter.
- Modify `src/shady_sim_deals/processors.py`: atomic rollback if sold-trait marking fails after transfer.
- Modify `src/shady_sim_deals/sims4_runtime.py`: inject both new adapters.
- Modify `tests/test_build.py`: exact tuning, localization, and DBPF assertions.
- Modify `tests/test_sims4_adapters.py`: trait registry and consequence mapping tests.
- Modify `tests/test_processors.py`: marker-failure rollback test.
- Modify `tests/test_runtime.py`: live runtime wiring assertions.
- Modify `README.md`, `ARCHITECTURE.md`, `DEVELOPMENT.md`, and `SPECS_CHECKLIST.md`: save semantics and completed consequence status.

---

### Task 1: Package the Visible Traits and Moodlets

**Files:**
- Create: `tuning/traits/family_asset_liquidator.xml`
- Create: `tuning/traits/outsourced_by_my_own_family.xml`
- Create: `tuning/traits/stork_claim_mysteriously_denied.xml`
- Create: `tuning/buffs/quarterly_profits_fewer_mouths.xml`
- Create: `tuning/buffs/love_had_a_return_policy.xml`
- Create: `tuning/buffs/nursery_has_been_downsized.xml`
- Modify: `localization/en_us.json`
- Modify: `build_mod.py`
- Test: `tests/test_build.py`

**Interfaces:**
- Produces trait instances `0xEAA21FFB1081E014`, `...015`, `...016`.
- Produces buff instances `0xEAA21FFB1081E017`, `...018`, `...019`.
- Produces `build_mod.TRAIT_TUNING_TYPE = 0xCB5FDDC7` and `build_mod.BUFF_TUNING_TYPE = 0x6017E896`.

- [ ] **Step 1: Write failing package tests**

Extend `EXPECTED_RESOURCE_KEYS` and add this test to `tests/test_build.py`:

```python
def test_sale_traits_and_moodlets_are_visible_localized_and_timed():
    resources = build_mod.package_resources()
    traits = {
        instance: ET.fromstring(data)
        for data, resource_type, _, instance in resources
        if resource_type == build_mod.TRAIT_TUNING_TYPE
    }
    buffs = {
        instance: ET.fromstring(data)
        for data, resource_type, _, instance in resources
        if resource_type == build_mod.BUFF_TUNING_TYPE
    }

    assert set(traits) == {
        0xEAA21FFB1081E014,
        0xEAA21FFB1081E015,
        0xEAA21FFB1081E016,
    }
    for instance, xml in traits.items():
        assert int(xml.attrib["s"]) == instance
        assert xml.find("./E[@n='trait_type']").text == "GAMEPLAY"
        assert xml.find("./T[@n='display_name']") is not None
        assert xml.find("./T[@n='trait_description']") is not None

    expected_buffs = {
        0xEAA21FFB1081E017: (14640, 4, 720),
        0xEAA21FFB1081E018: (14643, 6, 1440),
        0xEAA21FFB1081E019: (14643, 10, 2880),
    }
    assert set(buffs) == set(expected_buffs)
    for instance, (mood_type, weight, duration) in expected_buffs.items():
        xml = buffs[instance]
        assert int(xml.attrib["s"]) == instance
        assert int(xml.find("./T[@n='mood_type']").text) == mood_type
        assert int(xml.find("./T[@n='mood_weight']").text) == weight
        assert int(
            xml.find(
                "./V[@n='_temporary_commodity_info']/U/T[@n='max_duration']"
            ).text
        ) == duration
        assert xml.find("./T[@n='visible']").text == "True"

    strings = json.loads(
        (build_mod.ROOT / "localization" / "en_us.json").read_text("utf-8")
    )
    assert [strings["0xA110{:04X}".format(value)] for value in range(0x18, 0x24)] == [
        "Family Asset Liquidator",
        "Some Sims build family trees. This Sim trims them for quarterly growth and calls it logistics.",
        "Outsourced by My Own Family",
        "This Sim learned the family plan had an unsubscribe button, and somebody else clicked it.",
        "Stork Claim Mysteriously Denied",
        "The nursery plans vanished into a filing cabinet marked 'Definitely Not Our Department.'",
        "Quarterly Profits, Fewer Mouths",
        "The household budget is healthier, the headcount is lower, and ethics remain an optional expansion pack.",
        "Apparently, Love Had a Return Policy",
        "Nothing says unconditional love like being reassigned to an undisclosed buyer.",
        "The Nursery Has Been Downsized",
        "The crib is empty, the paperwork is sealed, and nobody can explain where tomorrow went.",
    ]
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_build.py
```

Expected: FAIL because `TRAIT_TUNING_TYPE`, `BUFF_TUNING_TYPE`, and the six resources do not exist.

- [ ] **Step 3: Add localization and exact trait XML**

Add keys `0xA1100018` through `0xA1100023` with the strings asserted above. Create each trait using this exact shape, changing `n`, `s`, name key, description key, and icon per row:

```xml
<I c="Trait" i="trait" m="traits.traits" n="ShadySimDeals_trait_FamilyAssetLiquidator" s="16907111114276462612">
  <L n="ages"><E>TEEN</E><E>ADULT</E><E>BABY</E><E>CHILD</E><E>TODDLER</E><E>ELDER</E><E>YOUNGADULT</E><E>INFANT</E></L>
  <T n="display_name">0xA1100018</T>
  <T n="display_name_gender_neutral">0xA1100018</T>
  <T n="icon">2f7d0004:00000000:47ffeedf30c4b115</T>
  <L n="species"><E /></L>
  <T n="trait_description">0xA1100019</T>
  <E n="trait_type">GAMEPLAY</E>
</I>
```

| File | `n` | `s` | Name | Description | Icon |
|---|---|---:|---|---|---|
| `family_asset_liquidator.xml` | `ShadySimDeals_trait_FamilyAssetLiquidator` | `0xEAA21FFB1081E014` decimal | `0xA1100018` | `0xA1100019` | `2f7d0004:00000000:47ffeedf30c4b115` |
| `outsourced_by_my_own_family.xml` | `ShadySimDeals_trait_OutsourcedByMyOwnFamily` | `0xEAA21FFB1081E015` decimal | `0xA110001A` | `0xA110001B` | `2f7d0004:00000000:8b841c91497034a5` |
| `stork_claim_mysteriously_denied.xml` | `ShadySimDeals_trait_StorkClaimMysteriouslyDenied` | `0xEAA21FFB1081E016` decimal | `0xA110001C` | `0xA110001D` | `2f7d0004:00000000:8b841c91497034a5` |

Use `int("EAA21FFB1081E014", 16)` when calculating the decimal `s` values; do not place hexadecimal text in `s`.

- [ ] **Step 4: Add exact buff XML**

Create each buff from this shape, changing `n`, `s`, duration, localization, mood, weight, category, and icon per row:

```xml
<I c="Buff" i="buff" m="buffs.buff" n="ShadySimDeals_buff_QuarterlyProfitsFewerMouths" s="16907111114276462615">
  <V n="_temporary_commodity_info" t="enabled"><U n="enabled"><L n="categories"><E>Happy_Buffs</E></L><T n="max_duration">720</T></U></V>
  <T n="audio_sting_on_add">39b2aa4a:00000000:8af8b916cf64c646</T>
  <T n="audio_sting_on_remove">39b2aa4a:00000000:3bf33216a25546ea</T>
  <T n="buff_description">0xA110001F</T>
  <T n="buff_name">0xA110001E</T>
  <T n="icon">2f7d0004:00000000:2357e4f259b6a63e</T>
  <T n="mood_type">14640</T>
  <T n="mood_weight">4</T>
  <T n="visible">True</T>
</I>
```

| File | Instance | Name/description | Mood/category | Weight | Duration | Icon |
|---|---:|---|---|---:|---:|---|
| `quarterly_profits_fewer_mouths.xml` | `...017` | `1E`/`1F` | `14640`/`Happy_Buffs` | 4 | 720 | `2357e4f259b6a63e` |
| `love_had_a_return_policy.xml` | `...018` | `20`/`21` | `14643`/`Sad_Buffs` | 6 | 1440 | `8b841c91497034a5` |
| `nursery_has_been_downsized.xml` | `...019` | `22`/`23` | `14643`/`Sad_Buffs` | 10 | 2880 | `8b841c91497034a5` |

- [ ] **Step 5: Package the six resources**

Add constants and entries to `build_mod.py`:

```python
TRAIT_TUNING_TYPE = 0xCB5FDDC7
BUFF_TUNING_TYPE = 0x6017E896
```

Append three `(path.read_bytes(), TRAIT_TUNING_TYPE, 0, instance)` and three equivalent `BUFF_TUNING_TYPE` tuples before the category resources. Extend `EXPECTED_RESOURCE_KEYS` with all six exact type/group/instance triples.

- [ ] **Step 6: Run package tests and build**

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_build.py
py -3.12 build_mod.py
```

Expected: package tests PASS; build reports both artifacts.

- [ ] **Step 7: Commit**

```powershell
git add build_mod.py localization/en_us.json tuning/traits tuning/buffs tests/test_build.py
git commit -m "feat: package sale traits and moodlets"
```

---

### Task 2: Replace the Live Sold Registry with the Sold Trait

**Files:**
- Modify: `src/shady_sim_deals/sims4_adapters.py`
- Modify: `src/shady_sim_deals/processors.py`
- Modify: `src/shady_sim_deals/sims4_runtime.py`
- Test: `tests/test_sims4_adapters.py`
- Test: `tests/test_processors.py`
- Test: `tests/test_runtime.py`

**Interfaces:**
- Produces `Sims4SoldSimRegistry(sim_info_lookup=None, trait_lookup=None)` with `mark_sold(sim_id)`, `is_sold(sim_id) -> bool`, and `unmark_sold(sim_id)`.
- Uses sold trait ID `0xEAA21FFB1081E015`.

- [ ] **Step 1: Write failing adapter and rollback tests**

Add to `tests/test_sims4_adapters.py`:

```python
def test_sold_registry_uses_sim_info_trait_tracker():
    sold_trait = object()

    class Tracker:
        def __init__(self):
            self.traits = set()

        def add_trait(self, trait):
            self.traits.add(trait)
            return True

        def has_trait(self, trait):
            return trait in self.traits

        def remove_trait(self, trait):
            self.traits.discard(trait)
            return True

    sim_info = type("SimInfo", (), {"trait_tracker": Tracker()})()
    registry = Sims4SoldSimRegistry(
        sim_info_lookup=lambda sim_id: sim_info,
        trait_lookup=lambda instance: sold_trait,
    )

    assert not registry.is_sold("7")
    registry.mark_sold("7")
    assert registry.is_sold("7")
    registry.unmark_sold("7")
    assert not registry.is_sold("7")
```

Add to `tests/test_processors.py`:

```python
def test_household_processor_rolls_back_transfer_when_sold_trait_fails():
    households = FakeHouseholds()

    class BrokenSoldRegistry:
        def mark_sold(self, sim_id):
            raise RuntimeError("trait unavailable")

        def unmark_sold(self, sim_id):
            pass

    processor = HouseholdMemberTargetProcessor(
        households, FakeOutcomes(), BrokenSoldRegistry()
    )
    transaction = SaleTransaction("household_member", "actor", "target", "home")

    with pytest.raises(RuntimeError, match="trait unavailable"):
        processor.process(transaction)

    assert households.transferred == ["target"]
    assert households.rolled_back == ["target"]
```

Add `import pytest` beside the existing imports and use the existing
`FakeHouseholds`, `FakeOutcomes`, and `SaleTransaction` helpers.

- [ ] **Step 2: Run tests and verify RED**

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_sims4_adapters.py tests/test_processors.py
```

Expected: import failure for `Sims4SoldSimRegistry` and missing rollback event.

- [ ] **Step 3: Implement the minimal game-backed registry**

Add to `sims4_adapters.py`:

```python
class Sims4SoldSimRegistry:
    SOLD_TRAIT_ID = 0xEAA21FFB1081E015

    def __init__(self, sim_info_lookup=None, trait_lookup=None):
        self._sim_info_lookup = (
            sim_info_lookup or Sims4TransactionValidator._find_sim_info
        )
        self._trait_lookup = trait_lookup or self._find_trait

    def _state(self, sim_id):
        sim_info = self._sim_info_lookup(str(sim_id))
        trait = self._trait_lookup(self.SOLD_TRAIT_ID)
        if sim_info is None or trait is None:
            raise IntegrationUnavailable("Sold trait state is unavailable")
        return sim_info.trait_tracker, trait

    def mark_sold(self, sim_id):
        tracker, trait = self._state(sim_id)
        if not tracker.has_trait(trait) and tracker.add_trait(trait) is False:
            raise IntegrationUnavailable("Sold trait could not be added")

    def is_sold(self, sim_id):
        tracker, trait = self._state(sim_id)
        return tracker.has_trait(trait)

    def unmark_sold(self, sim_id):
        tracker, trait = self._state(sim_id)
        if tracker.has_trait(trait) and tracker.remove_trait(trait) is False:
            raise IntegrationUnavailable("Sold trait could not be removed")

    @staticmethod
    def _find_trait(instance_id):
        import services
        import sims4.resources

        return services.get_instance_manager(
            sims4.resources.Types.TRAIT
        ).get(instance_id)
```

- [ ] **Step 4: Make processor marking atomic**

Wrap the transfer/mark boundary in `HouseholdMemberTargetProcessor.process`:

```python
def process(self, transaction):
    self._households.transfer_to_holding_household(transaction.target_id)
    try:
        self._sold.mark_sold(transaction.target_id)
    except Exception:
        self._households.rollback_transfer(transaction.target_id)
        raise
    transaction.outcome = self._outcomes.apply(transaction)
```

Do not call `unmark_sold` when `mark_sold` itself failed; the registry guarantees either the trait exists or it raises before reporting success.

- [ ] **Step 5: Inject the trait registry in live runtime**

Replace the `SoldSimRegistry` import and construction in `sims4_runtime.py` with `Sims4SoldSimRegistry`. Keep `registry.SoldSimRegistry` for pure domain tests only. Update the runtime test monkeypatch to assert `runtime["sold"]` is the injected fake `Sims4SoldSimRegistry`.

- [ ] **Step 6: Run focused and full tests**

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_sims4_adapters.py tests/test_processors.py tests/test_runtime.py
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests
```

Expected: all PASS.

- [ ] **Step 7: Commit**

```powershell
git add src/shady_sim_deals/sims4_adapters.py src/shady_sim_deals/processors.py src/shady_sim_deals/sims4_runtime.py tests/test_sims4_adapters.py tests/test_processors.py tests/test_runtime.py
git commit -m "fix: store sold state as a sim trait"
```

---

### Task 3: Apply Successful-Sale Traits and Moodlets

**Files:**
- Modify: `src/shady_sim_deals/sims4_adapters.py`
- Modify: `src/shady_sim_deals/sims4_runtime.py`
- Test: `tests/test_sims4_adapters.py`
- Test: `tests/test_runtime.py`

**Interfaces:**
- Produces `Sims4SaleConsequences(sim_info_lookup=None, trait_lookup=None, buff_lookup=None, logger=None)`.
- `apply(transaction)` never raises after a completed core sale; it logs `sale_consequences_failed` on integration errors.

- [ ] **Step 1: Write failing consequence mapping tests**

Add parameterized coverage to `tests/test_sims4_adapters.py`:

```python
class FakeConsequenceSimInfo:
    def __init__(self):
        self.events = []
        self.pending_trait = None
        self.trait_tracker = self

    def has_trait(self, trait):
        return any(event[0] == trait for event in self.events)

    def add_trait(self, trait):
        self.pending_trait = trait
        return True

    def add_buff(self, buff):
        self.events.append((self.pending_trait, buff))


@pytest.mark.parametrize(
    "transaction_type,expected_target",
    (
        ("household_member", ("sold", "sad")),
        ("unborn", ("lost", "extreme_sad")),
    ),
)
def test_sale_consequences_apply_exact_mapping(
    transaction_type, expected_target
):
    sims = {"actor": FakeConsequenceSimInfo(), "target": FakeConsequenceSimInfo()}
    tunings = {
        0xEAA21FFB1081E014: "seller",
        0xEAA21FFB1081E015: "sold",
        0xEAA21FFB1081E016: "lost",
        0xEAA21FFB1081E017: "happy",
        0xEAA21FFB1081E018: "sad",
        0xEAA21FFB1081E019: "extreme_sad",
    }
    adapter = Sims4SaleConsequences(
        sim_info_lookup=lambda sim_id: sims[sim_id],
        trait_lookup=lambda instance: tunings[instance],
        buff_lookup=lambda instance: tunings[instance],
    )
    transaction = type(
        "Transaction",
        (),
        {
            "transaction_type": transaction_type,
            "actor_id": "actor",
            "target_id": "target",
        },
    )()

    adapter.apply(transaction)

    assert sims["actor"].events == [("seller", "happy")]
    assert sims["target"].events == [expected_target]


def test_solo_unborn_sale_applies_only_seller_consequences_once():
    sim = FakeConsequenceSimInfo()
    adapter = Sims4SaleConsequences(
        sim_info_lookup=lambda sim_id: sim,
        trait_lookup=lambda instance: {
            0xEAA21FFB1081E014: "seller",
        }[instance],
        buff_lookup=lambda instance: {
            0xEAA21FFB1081E017: "happy",
        }[instance],
    )
    transaction = SaleTransaction("unborn", "actor", "actor", "home")

    adapter.apply(transaction)

    assert sim.events == [("seller", "happy")]
```

Add a second test whose `add_buff()` raises. Pass a fake logger with an
`exception(event, **fields)` method, assert `apply()` returns without raising,
and assert the recorded event is `sale_consequences_failed`.

- [ ] **Step 2: Run test and verify RED**

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_sims4_adapters.py -k consequences
```

Expected: import failure for `Sims4SaleConsequences`.

- [ ] **Step 3: Implement the shared adapter**

Add constants and this mapping to `sims4_adapters.py`:

```python
class Sims4SaleConsequences:
    SELLER_TRAIT_ID = 0xEAA21FFB1081E014
    SOLD_TRAIT_ID = 0xEAA21FFB1081E015
    LOST_UNBORN_TRAIT_ID = 0xEAA21FFB1081E016
    SELLER_BUFF_ID = 0xEAA21FFB1081E017
    SOLD_BUFF_ID = 0xEAA21FFB1081E018
    LOST_UNBORN_BUFF_ID = 0xEAA21FFB1081E019

    def __init__(
        self,
        sim_info_lookup=None,
        trait_lookup=None,
        buff_lookup=None,
        logger=None,
    ):
        self._sim_info_lookup = (
            sim_info_lookup or Sims4TransactionValidator._find_sim_info
        )
        self._trait_lookup = trait_lookup or self._find_trait
        self._buff_lookup = buff_lookup or self._find_buff
        self._logger = logger or ModLogger()

    def apply(self, transaction):
        try:
            self._apply_pair(
                transaction.actor_id,
                self.SELLER_TRAIT_ID,
                self.SELLER_BUFF_ID,
            )
            if transaction.transaction_type == "household_member":
                self._apply_pair(
                    transaction.target_id,
                    self.SOLD_TRAIT_ID,
                    self.SOLD_BUFF_ID,
                )
            elif transaction.actor_id != transaction.target_id:
                self._apply_pair(
                    transaction.target_id,
                    self.LOST_UNBORN_TRAIT_ID,
                    self.LOST_UNBORN_BUFF_ID,
                )
        except Exception:
            self._logger.exception(
                "sale_consequences_failed",
                transaction_type=transaction.transaction_type,
                actor_id=str(transaction.actor_id),
                target_id=str(transaction.target_id),
            )

    def _apply_pair(self, sim_id, trait_id, buff_id):
        sim_info = self._sim_info_lookup(str(sim_id))
        trait = self._trait_lookup(trait_id)
        buff = self._buff_lookup(buff_id)
        if sim_info is None or trait is None or buff is None:
            raise IntegrationUnavailable("Sale consequence tuning is unavailable")
        if (
            not sim_info.trait_tracker.has_trait(trait)
            and sim_info.trait_tracker.add_trait(trait) is False
        ):
            raise IntegrationUnavailable("Sale consequence trait could not be added")
        sim_info.add_buff(buff)
```

Import `ModLogger` once at module scope. Add `_find_buff` using
`services.get_instance_manager(Types.BUFF).get(instance_id)` and set
`_find_trait = staticmethod(Sims4SoldSimRegistry._find_trait)`.

- [ ] **Step 4: Inject one adapter into both workflows**

In `_runtime_services()`:

```python
consequences = Sims4SaleConsequences()
```

Pass `consequences` as the sixth argument to both `TransactionOrchestrator` instances, replacing both no-op `SimpleNamespace` objects. Extend the runtime test to assert both workflows share the same consequence object.

- [ ] **Step 5: Run focused and full tests**

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_sims4_adapters.py tests/test_runtime.py tests/test_transactions.py
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests
```

Expected: all PASS, including existing cancellation tests that assert consequences are absent.

- [ ] **Step 6: Commit**

```powershell
git add src/shady_sim_deals/sims4_adapters.py src/shady_sim_deals/sims4_runtime.py tests/test_sims4_adapters.py tests/test_runtime.py
git commit -m "feat: apply sale traits and moodlets"
```

---

### Task 4: Update Documentation and Verify the Deliverable

**Files:**
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`
- Modify: `DEVELOPMENT.md`
- Modify: `SPECS_CHECKLIST.md`

**Interfaces:**
- Consumes all six packaged tunings and both runtime adapters from Tasks 1–3.
- Produces a built, installable test artifact and an exact live-test checklist.

- [ ] **Step 1: Update documentation**

Make these exact documentation changes:

- `README.md`: replace session-local sold-marker wording with permanent visible traits that follow save/reload; list the three trait/moodlet outcomes.
- `ARCHITECTURE.md`: state live sold filtering reads the sold trait; reservations and rabbit-hole callbacks alone remain session-local.
- `DEVELOPMENT.md`: add household, shared-unborn, and solo-unborn consequence checks plus save/reload and exit-without-saving checks.
- `SPECS_CHECKLIST.md`: mark trait-backed sold persistence and seller/target moodlets complete; leave unrelated reactions and recovery commands pending.

- [ ] **Step 2: Run final automated verification**

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests
Get-ChildItem src/shady_sim_deals/*.py | ForEach-Object { py -3.12 -m py_compile $_.FullName }
py -3.12 build_mod.py
tar -tf dist/ShadySimDeals.ts4script
git diff --check
```

Expected: all tests PASS; compilation and build succeed; script archive lists every `shady_sim_deals/*.pyc`; `git diff --check` is silent.

- [ ] **Step 3: Commit documentation**

```powershell
git add README.md ARCHITECTURE.md DEVELOPMENT.md SPECS_CHECKLIST.md
git commit -m "docs: document sale consequences"
```

- [ ] **Step 4: Install only with the game closed**

Verify `Get-Process TS4_x64 -ErrorAction SilentlyContinue` returns nothing, then run:

```powershell
.\install_mod.ps1
```

Compare SHA-256 hashes for both `dist` files and the installed copies under `Mods/ShadySimDeals`; each pair must match.

- [ ] **Step 5: Live-test exact behavior**

1. Household sale: seller receives **Family Asset Liquidator** and **Quarterly Profits, Fewer Mouths**; target receives **Outsourced by My Own Family** and **Apparently, Love Had a Return Policy**.
2. Shared unborn sale: seller receives seller consequences; the other pregnant Sim receives **Stork Claim Mysteriously Denied** and **The Nursery Has Been Downsized**.
3. Solo unborn sale: pregnant seller receives only seller consequences.
4. Save after a sale and reload: permanent traits remain; expired moodlets do not reappear.
5. Reload a pre-sale save after exiting without saving: none of the new traits or moodlets remain.
6. Cancel before rabbit-hole completion: no trait, moodlet, target change, or payment occurs.

- [ ] **Step 6: Push the completed branch**

```powershell
git status --short
git push
```

Expected: clean worktree after push.
