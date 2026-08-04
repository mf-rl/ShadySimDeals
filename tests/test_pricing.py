from shady_sim_deals.models import BuyerContext, SaleCandidate
from shady_sim_deals.pricing import SimSalePricingService


def pricing():
    return SimSalePricingService()


def candidate(age="adult", **kwargs):
    return SaleCandidate("1", "Test Sim", age, **kwargs)


def test_younger_sims_have_higher_base_value():
    service = pricing()
    buyer = BuyerContext()
    assert service.calculate_household_member_offer(candidate("child"), buyer).amount > service.calculate_household_member_offer(candidate("elder"), buyer).amount


def test_unborn_multipliers():
    service = pricing()
    for count, expected in ((1, 15000), (2, 27000), (3, 36000)):
        target = candidate("adult", expected_offspring=count)
        assert service.calculate_unborn_offer(target, BuyerContext()).amount == expected


def test_modifiers_unknown_traits_caps_and_rounding():
    service = pricing()
    target = candidate(
        "adult",
        traits=("genius", "unsupported_trait"),
        skills=(10, 10, 10, 10),
        fame_level=2,
        occults=("vampire",),
        career_level=5,
        education="university",
    )
    offer = service.calculate_household_member_offer(target, BuyerContext(demand_multiplier=1.1))
    assert abs(offer.breakdown["trait_multiplier"] - 1.2) < 0.000001
    assert abs(offer.breakdown["skill_multiplier"] - 1.35) < 0.000001
    assert abs(offer.breakdown["fame_multiplier"] - 1.2) < 0.000001
    assert abs(offer.breakdown["occult_multiplier"] - 1.35) < 0.000001
    assert abs(offer.breakdown["status_multiplier"] - 1.27) < 0.000001
    assert offer.amount % 50 == 0


def test_price_caps_and_demand_are_deterministic():
    service = pricing()
    target = candidate("baby", traits=("genius",), skills=(10, 10, 10), fame_level=5, occults=("ghost", "vampire"))
    buyer = BuyerContext(demand_multiplier=1.4)
    first = service.calculate_household_member_offer(target, buyer)
    second = service.calculate_household_member_offer(target, buyer)
    assert first.amount == 50000
    assert first.amount == second.amount


def test_invalid_demand_is_rejected():
    service = pricing()
    target = candidate()
    buyer = BuyerContext(demand_multiplier=2.0)
    try:
        service.calculate_household_member_offer(target, buyer)
    except ValueError:
        return
    raise AssertionError("Invalid demand should be rejected")


def test_minimum_cap_and_risk_multiplier():
    target = candidate(
        "elder",
        traits=("lazy", "slob", "gloomy", "hot_headed", "erratic", "noncommittal"),
    )
    offer = pricing().calculate_household_member_offer(
        target, BuyerContext(demand_multiplier=0.8, risk_multiplier=0.5)
    )
    assert offer.amount == 1000
    assert offer.breakdown["risk_multiplier"] == 0.5