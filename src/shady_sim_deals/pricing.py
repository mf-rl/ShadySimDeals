"""Deterministic pricing domain service."""

from . import config
from .models import SaleOffer


def _round_to_fifty(value):
    return int((float(value) + 25.0) // 50.0) * 50


class SimSalePricingService:
    def calculate_household_member_offer(self, candidate, buyer_context, rare=False):
        pregnancy_bonus = 0
        if candidate.pregnant:
            pregnancy_bonus = int(
                config.BASE_PRICES["unborn"]
                * config.pregnancy_multiplier(candidate.expected_offspring)
            )
        return self._calculate(
            candidate,
            buyer_context,
            candidate.age,
            1.0,
            rare,
            special_bonus=pregnancy_bonus,
        )

    def calculate_unborn_offer(self, candidate, buyer_context, rare=False):
        multiplier = config.pregnancy_multiplier(candidate.expected_offspring)
        return self._calculate(candidate, buyer_context, "unborn", multiplier, rare)

    def _calculate(
        self,
        candidate,
        buyer_context,
        age_key,
        pregnancy_factor,
        rare,
        special_bonus=0,
    ):
        if age_key not in config.BASE_PRICES:
            raise ValueError("Unsupported age: {}".format(age_key))
        demand = buyer_context.demand_multiplier
        if not config.MARKET_DEMAND_MINIMUM <= demand <= config.MARKET_DEMAND_MAXIMUM:
            raise ValueError("Buyer demand multiplier is outside the configured range")

        trait_factor = 1.0 + sum(
            config.TRAIT_MODIFIERS.get(str(trait_id), 0.0)
            for trait_id in candidate.traits
        )
        skill_factor = 1.0 + self._skill_bonus(candidate.age, candidate.skills)
        fame_factor = 1.0 + config.FAME_MODIFIERS.get(candidate.fame_level, 0.0)
        occult_factor = 1.0 + sum(
            config.OCCULT_MODIFIERS.get(str(occult), 0.0)
            for occult in candidate.occults
        )
        status_factor = 1.0 + config.career_modifier(candidate.career_level)
        status_factor += config.EDUCATION_MODIFIERS.get(candidate.education, 0.0)
        risk_factor = max(0.0, buyer_context.risk_multiplier)
        base_price = config.BASE_PRICES[age_key]
        raw = (
            base_price
            * pregnancy_factor
            * trait_factor
            * skill_factor
            * fame_factor
            * occult_factor
            * status_factor
            * demand
            * risk_factor
            + special_bonus
        )
        maximum = config.MAXIMUM_RARE_OFFER if rare else config.MAXIMUM_OFFER
        amount = min(maximum, max(config.MINIMUM_OFFER, _round_to_fifty(raw)))
        return SaleOffer(
            amount,
            {
                "base_price": base_price,
                "pregnancy_multiplier": pregnancy_factor,
                "pregnancy_bonus": int(special_bonus),
                "trait_multiplier": trait_factor,
                "skill_multiplier": skill_factor,
                "fame_multiplier": fame_factor,
                "occult_multiplier": occult_factor,
                "status_multiplier": status_factor,
                "demand_multiplier": demand,
                "risk_multiplier": risk_factor,
            },
            buyer_context.buyer_id,
        )

    @staticmethod
    def _skill_bonus(age, skills):
        levels = sorted((max(0.0, float(level)) for level in skills), reverse=True)[:3]
        weights = (0.02, 0.01, 0.005)
        bonus = sum(level * weight for level, weight in zip(levels, weights))
        cap = config.CHILD_SKILL_CAP if age in ("toddler", "child") else config.ADULT_SKILL_CAP
        return min(cap, bonus)
