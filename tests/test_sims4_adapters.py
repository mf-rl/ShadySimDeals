import sys
from types import SimpleNamespace

import pytest

from shady_sim_deals import sims4_adapters
from shady_sim_deals.models import SaleTransaction


class FakeAge:
    def __init__(self, name):
        self.name = name


class FakeSimInfo:
    def __init__(
        self,
        age,
        sim_id="target",
        household_id="home",
        is_pet=False,
        instanced=True,
    ):
        self.age = FakeAge(age)
        self.sim_id = sim_id
        self.household_id = household_id
        self.is_pet = is_pet
        self.instanced = instanced

    def assign_to_household(self, household, assign_is_npc=True):
        self.household_id = None if household is None else household.id

    def get_sim_instance(self):
        return self if self.instanced else None


def test_sold_registry_uses_sim_info_trait_tracker():
    sold_trait = object()

    class SimInfo:
        def __init__(self):
            self.traits = set()
            self.trait_tracker = object()

        def add_trait(self, trait):
            self.traits.add(trait)
            return True

        def has_trait(self, trait):
            return trait in self.traits

        def remove_trait(self, trait):
            self.traits.discard(trait)
            return True

    sim_info = SimInfo()
    registry = sims4_adapters.Sims4SoldSimRegistry(
        sim_info_lookup=lambda sim_id: sim_info,
        trait_lookup=lambda instance: sold_trait,
    )

    assert not registry.is_sold("7")
    registry.mark_sold("7")
    assert registry.is_sold("7")
    registry.unmark_sold("7")
    assert not registry.is_sold("7")


class FakeConsequenceSimInfo:
    def __init__(self, hidden=False):
        self.events = []
        self.pending_trait = None
        self.trait_tracker = object()
        self.sim_instance = SimpleNamespace(add_buff=self._record_buff)
        self.hidden = hidden

    def has_trait(self, trait):
        return any(event[0] == trait for event in self.events)

    def add_trait(self, trait):
        self.pending_trait = trait
        return True

    def _record_buff(self, buff):
        self.events.append((self.pending_trait, buff))

    def get_sim_instance(self, allow_hidden_flags=None):
        if self.hidden and allow_hidden_flags is None:
            return None
        return self.sim_instance


@pytest.fixture
def all_hidden_reasons(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "objects",
        SimpleNamespace(ALL_HIDDEN_REASONS=object()),
    )


@pytest.mark.parametrize(
    "transaction_type,expected_target",
    (
        ("household_member", ("sold", "sad")),
        ("unborn", ("lost", "extreme_sad")),
    ),
)
def test_sale_consequences_apply_exact_mapping(
    transaction_type, expected_target, all_hidden_reasons
):
    sims = {
        "actor": FakeConsequenceSimInfo(),
        "target": FakeConsequenceSimInfo(hidden=True),
    }
    tunings = {
        0xEAA21FFB1081E014: "seller",
        0xEAA21FFB1081E015: "sold",
        0xEAA21FFB1081E016: "lost",
        0xEAA21FFB1081E017: "happy",
        0xEAA21FFB1081E018: "sad",
        0xEAA21FFB1081E019: "extreme_sad",
    }
    adapter = sims4_adapters.Sims4SaleConsequences(
        sim_info_lookup=lambda sim_id: sims[sim_id],
        trait_lookup=lambda instance: tunings[instance],
        buff_lookup=lambda instance: tunings[instance],
    )
    transaction = SaleTransaction(
        transaction_type, "actor", "target", "home"
    )

    adapter.apply(transaction)

    assert sims["actor"].events == [("seller", "happy")]
    assert sims["target"].events == [expected_target]


def test_solo_unborn_sale_applies_only_seller_consequences_once(
    all_hidden_reasons,
):
    sim = FakeConsequenceSimInfo()
    adapter = sims4_adapters.Sims4SaleConsequences(
        sim_info_lookup=lambda sim_id: sim,
        trait_lookup=lambda instance: {
            0xEAA21FFB1081E014: "seller",
        }[instance],
        buff_lookup=lambda instance: {
            0xEAA21FFB1081E017: "happy",
        }[instance],
    )

    adapter.apply(SaleTransaction("unborn", "actor", "actor", "home"))

    assert sim.events == [("seller", "happy")]


def test_sale_consequence_failure_is_logged_without_raising(
    all_hidden_reasons,
):
    class BrokenSim(FakeConsequenceSimInfo):
        def __init__(self):
            super().__init__()
            self.sim_instance = SimpleNamespace(
                add_buff=lambda buff: (_ for _ in ()).throw(
                    RuntimeError("buff unavailable")
                )
            )

    class FakeLogger:
        def __init__(self):
            self.events = []

        def exception(self, event, **fields):
            self.events.append((event, fields))

    logger = FakeLogger()
    adapter = sims4_adapters.Sims4SaleConsequences(
        sim_info_lookup=lambda sim_id: BrokenSim(),
        trait_lookup=lambda instance: object(),
        buff_lookup=lambda instance: object(),
        logger=logger,
    )

    adapter.apply(SaleTransaction("household_member", "actor", "target", "home"))

    assert logger.events[0][0] == "sale_consequences_failed"


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
    def __init__(
        self, households, fail_created_add=False, switch_result=True
    ):
        self.households = list(households)
        self.fail_created_add = fail_created_add
        self.switch_result = switch_result
        self.switch_calls = []

    def values(self):
        return tuple(self.households)

    def get(self, household_id):
        return next((h for h in self.households if h.id == household_id), None)

    def create_household(self, account, starting_funds):
        household = FakeHousehold("holdings", starting_funds, account)
        household.fail_add = self.fail_created_add
        self.households.append(household)
        return household

    def switch_sim_from_household_to_target_household(
        self,
        sim_info,
        starting_household,
        destination_household,
        destroy_if_empty_household=False,
        reason=None,
    ):
        self.switch_calls.append(
            (
                sim_info,
                starting_household,
                destination_household,
                destroy_if_empty_household,
                reason,
            )
        )
        if not self.switch_result:
            return False
        starting_household.remove_sim_info(
            sim_info,
            destroy_if_empty_household=destroy_if_empty_household,
            assign_to_none=False,
        )
        destination_household.add_sim_info_to_household(sim_info, reason=reason)
        return True


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


class FakeRabbitHoleService:
    def __init__(self, rabbit_hole_id=91, callback_error=None):
        self.rabbit_hole_id = rabbit_hole_id
        self.rabbit_hole = object()
        self.callback_error = callback_error
        self.started = []
        self.managed = []
        self.callback_key = None
        self.callback = None
        self.callback_registrations = []
        self.removed = []

    def put_sims_in_shared_rabbithole(self, sim_infos, rabbit_hole_type):
        self.started.append((sim_infos, rabbit_hole_type))
        return self.rabbit_hole_id

    def put_sim_in_managed_rabbithole(self, sim_info, rabbit_hole_type):
        self.managed.append((sim_info, rabbit_hole_type))
        return self.rabbit_hole_id

    def set_rabbit_hole_expiration_callback(
        self, sim_id, rabbit_hole_id, callback
    ):
        if self.callback_error is not None:
            raise self.callback_error
        self.callback_key = (sim_id, rabbit_hole_id)
        self.callback = callback
        self.callback_registrations.append(
            (sim_id, rabbit_hole_id, callback)
        )

    def _get_rabbit_hole(self, sim_id, rabbit_hole_id):
        return self.rabbit_hole

    def remove_sim_from_rabbit_hole(
        self, sim_id, rabbit_hole_id, canceled=False
    ):
        self.removed.append((sim_id, rabbit_hole_id, canceled))


@pytest.fixture
def household_change_origin(monkeypatch):
    origin = SimpleNamespace(UNKNOWN="unknown")
    household_enums = SimpleNamespace(HouseholdChangeOrigin=origin)
    monkeypatch.setitem(
        sys.modules, "sims", SimpleNamespace(household_enums=household_enums)
    )
    monkeypatch.setitem(sys.modules, "sims.household_enums", household_enums)
    return origin


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


def test_age_key_rejects_unsupported_game_age():
    with pytest.raises(ValueError, match="Unsupported age"):
        sims4_adapters.age_key(FakeSimInfo("UNKNOWN"))


@pytest.mark.parametrize(
    ("age", "expected_type"),
    (
        ("ELDER", 0xEAA21FFB1081E005),
        ("BABY", 0xEAA21FFB1081E006),
        ("CHILD", 0xEAA21FFB1081E006),
        ("TEEN", 0xEAA21FFB1081E007),
        ("ADULT", 0xEAA21FFB1081E007),
    ),
)
def test_rabbit_hole_adapter_starts_shared_hole_in_participant_order(
    age, expected_type
):
    actor = FakeSimInfo("ADULT", sim_id="1")
    target = FakeSimInfo(age, sim_id="2")
    callbacks = []
    service = FakeRabbitHoleService()
    adapter = sims4_adapters.Sims4RabbitHoleAdapter(
        rabbit_hole_service=service,
        sim_info_lookup={"1": actor, "2": target}.get,
        rabbit_hole_lookup=lambda instance: instance,
    )
    deal = SaleTransaction("household_member", "1", "2", "home")

    assert adapter.run(deal, callbacks.append) is True
    assert service.started == [([actor, target], expected_type)]
    assert service.callback_key == (actor.sim_id, service.rabbit_hole_id)

    service.callback(canceled=False)
    assert callbacks == [False]


def test_rabbit_hole_callback_reattaches_after_cas_resets_hole():
    actor = FakeSimInfo("ADULT", sim_id="cas-actor")
    target = FakeSimInfo("CHILD", sim_id="cas-target")
    callbacks = []
    service = FakeRabbitHoleService()
    adapter = sims4_adapters.Sims4RabbitHoleAdapter(
        rabbit_hole_service=service,
        sim_info_lookup={
            "cas-actor": actor,
            "cas-target": target,
        }.get,
        rabbit_hole_lookup=lambda instance: instance,
    )
    adapter.run(
        SaleTransaction(
            "household_member", "cas-actor", "cas-target", "home"
        ),
        callbacks.append,
    )
    original_callback = service.callback

    sims4_adapters.mark_rabbit_hole_callback_for_reattach(actor.sim_id)
    sims4_adapters.reattach_rabbit_hole_callback(
        actor.sim_id, service.rabbit_hole_id, service
    )

    assert service.callback_registrations == [
        (actor.sim_id, service.rabbit_hole_id, original_callback),
        (actor.sim_id, service.rabbit_hole_id, original_callback),
    ]
    service.callback(canceled=False)
    assert callbacks == [False]


def test_rabbit_hole_adapter_rejects_missing_participant():
    actor = FakeSimInfo("ADULT", sim_id="1")
    adapter = sims4_adapters.Sims4RabbitHoleAdapter(
        rabbit_hole_service=FakeRabbitHoleService(),
        sim_info_lookup={"1": actor}.get,
        rabbit_hole_lookup=lambda instance: instance,
    )
    deal = SaleTransaction("household_member", "1", "2", "home")

    with pytest.raises(
        sims4_adapters.IntegrationUnavailable, match="participant"
    ):
        adapter.run(deal, lambda canceled: None)


def test_rabbit_hole_adapter_rejects_failed_startup():
    actor = FakeSimInfo("ADULT", sim_id="1")
    target = FakeSimInfo("CHILD", sim_id="2")
    adapter = sims4_adapters.Sims4RabbitHoleAdapter(
        rabbit_hole_service=FakeRabbitHoleService(rabbit_hole_id=None),
        sim_info_lookup={"1": actor, "2": target}.get,
        rabbit_hole_lookup=lambda instance: instance,
    )
    deal = SaleTransaction("household_member", "1", "2", "home")

    with pytest.raises(
        sims4_adapters.IntegrationUnavailable, match="could not start"
    ):
        adapter.run(deal, lambda canceled: None)


def test_rabbit_hole_adapter_cancels_started_hole_if_callback_setup_fails():
    actor = FakeSimInfo("ADULT", sim_id="1")
    target = FakeSimInfo("CHILD", sim_id="2")
    service = FakeRabbitHoleService(callback_error=RuntimeError("callback failed"))
    adapter = sims4_adapters.Sims4RabbitHoleAdapter(
        rabbit_hole_service=service,
        sim_info_lookup={"1": actor, "2": target}.get,
        rabbit_hole_lookup=lambda instance: instance,
    )
    deal = SaleTransaction("household_member", "1", "2", "home")

    with pytest.raises(RuntimeError, match="callback failed"):
        adapter.run(deal, lambda canceled: None)

    assert service.removed == [(actor.sim_id, service.rabbit_hole_id, True)]


def test_rabbit_hole_completion_does_not_wait_for_sims_to_reinstance():
    actor = FakeSimInfo("ADULT", sim_id="1", instanced=False)
    target = FakeSimInfo("CHILD", sim_id="2", instanced=False)
    callbacks = []
    service = FakeRabbitHoleService()
    adapter = sims4_adapters.Sims4RabbitHoleAdapter(
        rabbit_hole_service=service,
        sim_info_lookup={"1": actor, "2": target}.get,
        rabbit_hole_lookup=lambda instance: instance,
    )
    adapter.run(
        SaleTransaction("household_member", "1", "2", "home"),
        callbacks.append,
    )

    service.callback(canceled=False)

    assert callbacks == [False]


def test_unborn_rabbit_hole_uses_one_participant_for_pregnant_actor():
    actor = FakeSimInfo("ADULT", sim_id="1")
    service = FakeRabbitHoleService()
    adapter = sims4_adapters.Sims4RabbitHoleAdapter(
        rabbit_hole_service=service,
        sim_info_lookup={"1": actor}.get,
        rabbit_hole_lookup=lambda instance: instance,
        expected_offspring_lookup=lambda sim_id: 1,
    )
    deal = SaleTransaction("unborn", "1", "1", "home")

    assert adapter.run(deal, lambda canceled: None) is True
    assert service.managed == [(actor, 0xEAA21FFB1081E00B)]
    assert service.started == []


def test_unborn_rabbit_hole_uses_actor_then_pregnant_target():
    actor = FakeSimInfo("ADULT", sim_id="1")
    target = FakeSimInfo("ADULT", sim_id="2")
    service = FakeRabbitHoleService()
    adapter = sims4_adapters.Sims4RabbitHoleAdapter(
        rabbit_hole_service=service,
        sim_info_lookup={"1": actor, "2": target}.get,
        rabbit_hole_lookup=lambda instance: instance,
        expected_offspring_lookup=lambda sim_id: 1,
    )
    deal = SaleTransaction("unborn", "1", "2", "home")

    assert adapter.run(deal, lambda canceled: None) is True
    assert service.started == [([actor, target], 0xEAA21FFB1081E00C)]
    assert service.managed == []


@pytest.mark.parametrize(
    ("count", "solo_id", "shared_id"),
    (
        (1, 0xEAA21FFB1081E00B, 0xEAA21FFB1081E00C),
        (2, 0xEAA21FFB1081E00D, 0xEAA21FFB1081E00E),
        (3, 0xEAA21FFB1081E00F, 0xEAA21FFB1081E010),
        (4, 0xEAA21FFB1081E00F, 0xEAA21FFB1081E010),
    ),
)
def test_unborn_rabbit_hole_selects_offspring_duration(count, solo_id, shared_id):
    actor = FakeSimInfo("ADULT", sim_id="1")
    target = FakeSimInfo("ADULT", sim_id="2")
    lookup = {"1": actor, "2": target}.get
    solo_service = FakeRabbitHoleService()
    solo = sims4_adapters.Sims4RabbitHoleAdapter(
        rabbit_hole_service=solo_service,
        sim_info_lookup=lookup,
        rabbit_hole_lookup=lambda instance: instance,
        expected_offspring_lookup=lambda sim_id: count,
    )
    solo.run(SaleTransaction("unborn", "1", "1", "home"), lambda canceled: None)

    shared_service = FakeRabbitHoleService()
    shared = sims4_adapters.Sims4RabbitHoleAdapter(
        rabbit_hole_service=shared_service,
        sim_info_lookup=lookup,
        rabbit_hole_lookup=lambda instance: instance,
        expected_offspring_lookup=lambda sim_id: count,
    )
    shared.run(SaleTransaction("unborn", "1", "2", "home"), lambda canceled: None)

    assert solo_service.managed == [(actor, solo_id)]
    assert shared_service.started == [([actor, target], shared_id)]


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

    sims["target"].age = FakeAge("UNKNOWN")
    assert validator().validate(deal) == "Unsupported age: UNKNOWN"
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
    assert (
        validator(reserved=lambda sim_id: sim_id == "target").validate(
            deal, check_reservations=False
        )
        is None
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


def test_household_adapter_moves_target_to_reused_hidden_holdings_and_rolls_back(
    household_change_origin,
):
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
    assert manager.switch_calls == [
        (target, source, existing, False, household_change_origin.UNKNOWN),
        (target, existing, source, False, household_change_origin.UNKNOWN),
    ]


def test_household_adapter_uses_current_manager_after_save_reload(
    monkeypatch, household_change_origin
):
    first_target = FakeSimInfo("TEEN")
    first_source = FakeHousehold()
    first_source.sim_infos.append(first_target)
    first_manager = FakeHouseholdManager((first_source,))
    current_target = [first_target]
    current_manager = [first_manager]
    monkeypatch.setitem(
        sys.modules,
        "services",
        SimpleNamespace(household_manager=lambda: current_manager[0]),
    )
    adapter = sims4_adapters.Sims4HouseholdAdapter(
        sim_info_lookup=lambda sim_id: current_target[0]
    )

    adapter.transfer_to_holding_household("target")

    second_target = FakeSimInfo("TEEN")
    second_source = FakeHousehold()
    second_source.sim_infos.append(second_target)
    second_manager = FakeHouseholdManager((second_source,))
    first_manager.households.clear()
    current_target[0] = second_target
    current_manager[0] = second_manager

    adapter.transfer_to_holding_household("target")

    assert second_target not in second_source.sim_infos
    assert second_target in second_manager.get("holdings").sim_infos


def test_household_adapter_restores_source_when_holding_add_fails(
    household_change_origin,
):
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


def test_household_adapter_rejects_failed_native_switch(
    household_change_origin,
):
    target = FakeSimInfo("CHILD")
    source = FakeHousehold()
    source.sim_infos.append(target)
    manager = FakeHouseholdManager((source,), switch_result=False)
    adapter = sims4_adapters.Sims4HouseholdAdapter(
        household_manager=manager,
        sim_info_lookup=lambda sim_id: target if sim_id == "target" else None,
    )

    with pytest.raises(sims4_adapters.IntegrationUnavailable, match="transfer failed"):
        adapter.transfer_to_holding_household("target")

    assert target in source.sim_infos
    assert target.household_id == "home"
    assert len(manager.switch_calls) == 1


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
