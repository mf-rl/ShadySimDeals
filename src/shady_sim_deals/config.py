"""Central read-only configuration for ShadySimDeals."""

from types import MappingProxyType


BASE_PRICES = MappingProxyType(
    {
        "unborn": 15000,
        "baby": 13500,
        "infant": 12000,
        "toddler": 10000,
        "child": 8000,
        "teen": 6500,
        "young_adult": 5000,
        "adult": 4000,
        "elder": 2500,
    }
)

PREGNANCY_MULTIPLIERS = MappingProxyType({1: 1.0, 2: 1.8, 3: 2.4})
TRAIT_MODIFIERS = MappingProxyType(
    {
        "genius": 0.20,
        "creative": 0.15,
        "active": 0.10,
        "self_assured": 0.12,
        "ambitious": 0.15,
        "cheerful": 0.08,
        "good": 0.05,
        "lazy": -0.10,
        "slob": -0.12,
        "gloomy": -0.08,
        "hot_headed": -0.10,
        "erratic": -0.15,
        "noncommittal": -0.08,
    }
)
FAME_MODIFIERS = MappingProxyType({1: 0.10, 2: 0.20, 3: 0.35, 4: 0.50, 5: 0.75})
OCCULT_MODIFIERS = MappingProxyType(
    {
        "alien": 0.30,
        "vampire": 0.35,
        "spellcaster": 0.30,
        "werewolf": 0.25,
        "mermaid": 0.25,
        "ghost": 0.40,
    }
)
EDUCATION_MODIFIERS = MappingProxyType(
    {"high_school": 0.05, "university": 0.15, "distinguished": 0.25}
)

MINIMUM_OFFER = 1000
MAXIMUM_OFFER = 50000
MAXIMUM_RARE_OFFER = 100000
ADULT_SKILL_CAP = 0.35
CHILD_SKILL_CAP = 0.10
MARKET_DEMAND_MINIMUM = 0.80
MARKET_DEMAND_MAXIMUM = 1.40

OUTCOME_WEIGHTS = MappingProxyType(
    {
        "hidden": 80,
        "escape": 12,
        "ghost": 5,
        "reversed": 3,
    }
)
CHILD_AGES = frozenset(("baby", "infant", "toddler", "child"))
HOUSEHOLD_SALE_AGES = frozenset(("teen", "young_adult", "adult", "elder"))
HOUSEHOLD_RABBIT_HOLE_MINUTES = MappingProxyType(
    {
        "baby": 90,
        "infant": 90,
        "toddler": 90,
        "child": 90,
        "teen": 120,
        "young_adult": 120,
        "adult": 120,
        "elder": 75,
    }
)


def pregnancy_multiplier(expected_offspring):
    """Return an extensible total multiplier for one or more unborn children."""
    count = max(1, int(expected_offspring or 1))
    if count in PREGNANCY_MULTIPLIERS:
        return PREGNANCY_MULTIPLIERS[count]
    return PREGNANCY_MULTIPLIERS[3] + ((count - 3) * 0.60)


def unborn_rabbit_hole_minutes(expected_offspring):
    count = max(1, int(expected_offspring or 1))
    return min(180, 90 + max(0, count - 1) * 30)


def career_modifier(level):
    level = max(0, min(10, int(level or 0)))
    if level <= 3:
        return level * 0.02
    if level <= 7:
        return 0.06 + ((level - 3) * 0.03)
    return 0.18 + ((level - 7) * 0.04)
