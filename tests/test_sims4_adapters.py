import sys
from types import SimpleNamespace

import pytest

from shady_sim_deals import sims4_adapters
from shady_sim_deals.models import SaleTransaction


class FakeAge:
    def __init__(self, name):
        self.name = name


class FakeSimInfo:
    def __init__(self, age, sim_id="target", household_id="home", is_pet=False):
        self.age = FakeAge(age)
        self.sim_id = sim_id
        self.household_id = household_id
        self.is_pet = is_pet

    def assign_to_household(self, household, assign_is_npc=True):
        self.household_id = None if household is None else household.id


class FakeHousehold:
    def __init__(self, household_id="home", funds=object(), account="account"):
        self.id = household_id
        self.funds = funds
        self.account = account
        self.name = "Source"
        self.hidden = False
        self.sim_infos = []
        self.fail_add = False

    def set_to_hidden(self, family_funds):
        self.hidden = True

    def remove_sim_info(
        self,
        sim_info,
        destroy_if_empty_household=False,
        process_events=True,
        assign_to_none=True,
    ):
        self.sim_infos.remove(sim_info)
        if assign_to_none:
            sim_info.assign_to_household(None, assign_is_npc=False)

    def add_sim_info_to_household(self, sim_info, reason=None):
        if self.fail_add:
            raise RuntimeError("add failed")
        sim_info.assign_to_household(self)
        self.sim_infos.append(sim_info)


class FakeHouseholdManager:
    def __init__(self, households, fail_created_add=False):
        self.households = list(households)
        self.fail_created_add = fail_created_add

    def values(self):
        return tuple(self.households)

    def get(self, household_id):
        return next((h for h in self.households if h.id == household_id), None)

    def create_household(self, account, starting_funds):
        household = FakeHousehold("holdings", starting_funds, account)
        household.fail_add = self.fail_created_add
        self.households.append(household)
        return household


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


def test_age_key_maps_supported_game_ages():
    assert sims4_adapters.age_key(FakeSimInfo("TEEN")) == "teen"
    assert sims4_adapters.age_key(FakeSimInfo("YOUNGADULT")) == "young_adult"
    assert sims4_adapters.age_key(FakeSimInfo("ADULT")) == "adult"
    assert sims4_adapters.age_key(FakeSimInfo("ELDER")) == "elder"


def test_age_key_rejects_unsupported_game_age():
    with pytest.raises(ValueError, match="Unsupported age"):
        sims4_adapters.age_key(FakeSimInfo("CHILD"))


def test_transaction_validator_accepts_only_safe_current_household_targets():
    sims = {
        "actor": FakeSimInfo("ADULT", sim_id="actor"),
        "target": FakeSimInfo("TEEN"),
    }
    households = {"home": FakeHousehold()}

    def validator(reserved=lambda _: False, shutting_down=lambda: False):
        return sims4_adapters.Sims4TransactionValidator(
            sim_info_lookup=sims.get,
            household_lookup=households.get,
            reservation_check=reserved,
            shutdown_check=shutting_down,
        )

    deal = SaleTransaction("household_member", "actor", "target", "home")
    assert validator().validate(deal) is None

    missing_actor = SaleTransaction("household_member", "missing", "target", "home")
    assert validator().validate(missing_actor) == "Actor no longer exists"

    same_sim = SaleTransaction("household_member", "actor", "actor", "home")
    assert validator().validate(same_sim) == "The actor cannot be the target"

    sims["target"].age = FakeAge("CHILD")
    assert validator().validate(deal) == "Unsupported age: CHILD"
    sims["target"].age = FakeAge("TEEN")

    sims["target"].is_pet = True
    assert validator().validate(deal) == "Pets are not supported"
    sims["target"].is_pet = False

    sims["target"].household_id = "elsewhere"
    assert validator().validate(deal) == "Target left the active household"
    sims["target"].household_id = "home"

    assert validator(reserved=lambda sim_id: sim_id == "target").validate(deal) == (
        "A transaction participant is already reserved"
    )
    assert validator(shutting_down=lambda: True).validate(deal) == (
        "The game is shutting down"
    )

    households["home"].funds = None
    assert validator().validate(deal) == "Household funds are unavailable"


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


def test_household_adapter_moves_target_to_reused_hidden_holdings_and_rolls_back():
    target = FakeSimInfo("TEEN")
    source = FakeHousehold()
    source.sim_infos.append(target)
    existing = FakeHousehold("holdings", 0)
    existing.name = "ShadySimDeals Holdings"
    existing.set_to_hidden(0)
    manager = FakeHouseholdManager((source, existing))
    adapter = sims4_adapters.Sims4HouseholdAdapter(
        household_manager=manager,
        sim_info_lookup=lambda sim_id: target if sim_id == "target" else None,
    )

    adapter.transfer_to_holding_household("target")

    assert target not in source.sim_infos
    assert target in existing.sim_infos
    assert adapter.is_transfer_complete("target")
    assert len(manager.households) == 2

    adapter.rollback_transfer("target")

    assert target in source.sim_infos
    assert target not in existing.sim_infos
    assert target.household_id == "home"


def test_household_adapter_restores_source_when_holding_add_fails():
    target = FakeSimInfo("TEEN")
    source = FakeHousehold()
    source.sim_infos.append(target)
    manager = FakeHouseholdManager((source,), fail_created_add=True)
    adapter = sims4_adapters.Sims4HouseholdAdapter(
        household_manager=manager,
        sim_info_lookup=lambda sim_id: target if sim_id == "target" else None,
    )

    with pytest.raises(sims4_adapters.IntegrationUnavailable, match="transfer failed"):
        adapter.transfer_to_holding_household("target")

    assert target in source.sim_infos
    assert target.household_id == "home"
    holdings = manager.get("holdings")
    assert holdings.hidden


def test_funds_adapter_uses_marketplace_sale_telemetry_reason(monkeypatch):
    calls = []
    household = SimpleNamespace(
        funds=SimpleNamespace(add=lambda amount, reason: calls.append((amount, reason)))
    )
    services = SimpleNamespace(
        household_manager=lambda: SimpleNamespace(get=lambda household_id: household)
    )
    consts = SimpleNamespace(TELEMETRY_MONEY_OBJECT_MARKETPLACE_SALE=25)
    monkeypatch.setitem(sys.modules, "services", services)
    monkeypatch.setitem(
        sys.modules,
        "protocolbuffers",
        SimpleNamespace(Consts_pb2=consts),
    )

    sims4_adapters.Sims4FundsAdapter().deposit("7", 6500)

    assert calls == [(6500, 25)]


def test_funds_adapter_refund_removes_full_marketplace_payment(monkeypatch):
    calls = []
    funds = SimpleNamespace(
        try_remove=lambda amount, reason, sim, require_full: calls.append(
            (amount, reason, sim, require_full)
        )
        or True
    )
    household = SimpleNamespace(funds=funds)
    services = SimpleNamespace(
        household_manager=lambda: SimpleNamespace(get=lambda household_id: household)
    )
    consts = SimpleNamespace(TELEMETRY_MONEY_OBJECT_MARKETPLACE_SALE=25)
    monkeypatch.setitem(sys.modules, "services", services)
    monkeypatch.setitem(
        sys.modules,
        "protocolbuffers",
        SimpleNamespace(Consts_pb2=consts),
    )

    sims4_adapters.Sims4FundsAdapter().withdraw("7", 15000)

    assert calls == [(15000, 25, None, True)]
