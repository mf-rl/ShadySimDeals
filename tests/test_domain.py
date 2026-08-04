import random

from shady_sim_deals.filtering import household_member_candidates, unborn_candidates
from shady_sim_deals.models import SimRecord
from shady_sim_deals.outcomes import WeightedOutcomeSelector
from shady_sim_deals.reactions import PregnantSimReactionService, SellerReactionService
from shady_sim_deals.state_machine import InvalidTransitionError, TransactionStateMachine


def test_picker_filters_actor_sold_invalid_reserved_and_pets():
    records = (
        SimRecord("actor", "home", pregnant=True),
        SimRecord("valid", "home"),
        SimRecord("sold", "home", sold=True),
        SimRecord("invalid", "home", valid=False),
        SimRecord("reserved", "home", reserved=True),
        SimRecord("pet", "home", is_pet=True),
        SimRecord("other", "elsewhere"),
    )
    assert [item.sim_id for item in household_member_candidates(records, "actor", "home")] == ["valid"]
    assert [item.sim_id for item in unborn_candidates(records, "home")] == ["actor"]


def test_playable_household_picker_supports_all_configured_ages():
    ages = (
        "baby",
        "infant",
        "toddler",
        "child",
        "teen",
        "young_adult",
        "adult",
        "elder",
    )
    records = tuple(SimRecord(age, "home", age=age) for age in ages)
    assert [
        record.age
        for record in household_member_candidates(records, "actor", "home")
    ] == list(ages)


def test_invalid_state_transition_is_rejected():
    transaction = type("Transaction", (), {"state": "created"})()
    state_machine = TransactionStateMachine()
    try:
        state_machine.transition(transaction, "completed")
    except InvalidTransitionError:
        return
    raise AssertionError("Invalid transition should be rejected")


def test_outcomes_are_seeded_and_child_ghost_is_disabled():
    first = WeightedOutcomeSelector(random.Random(8))
    second = WeightedOutcomeSelector(random.Random(8))
    assert [first.select("adult") for _ in range(20)] == [second.select("adult") for _ in range(20)]
    child_selector = WeightedOutcomeSelector(random.Random(2), {"hidden": 0, "ghost": 100})
    assert child_selector.select("child") == "hidden"


def test_weighted_outcome_boundaries():
    random_source = type("RandomSource", (), {"random": lambda self: 0.79})()
    selector = WeightedOutcomeSelector(random_source, {"hidden": 80, "ghost": 20})
    assert selector.select("adult") == "hidden"
    random_source.random = lambda: 0.81
    assert selector.select("adult") == "ghost"


def test_seller_reaction_priorities():
    service = SellerReactionService()
    assert service.select(("good",), "household_member", 50000, 10000) == "sudden_attack_of_conscience"
    assert service.select(("evil",), "household_member", 5000, 10000) == "sold_below_market_value"
    assert service.select(("evil",), "household_member", 10000, 10000) == "household_is_finally_profitable"
    assert service.select((), "unborn", 10000, 10000) == "nooboo_futures_are_up"
    assert service.select((), "household_member", 20000, 10000) == "worth_every_relative"


def test_pregnant_reaction_is_injectable():
    assert PregnantSimReactionService(random.Random(1)).select(60) == "complicit"
    assert PregnantSimReactionService(random.Random(5)).select(-10) == "betrayed"
