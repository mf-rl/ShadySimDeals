"""Pure domain models with no dependency on The Sims 4 runtime."""

import uuid


class SimRecord:
    def __init__(
        self,
        sim_id,
        household_id,
        age="adult",
        pregnant=False,
        valid=True,
        sold=False,
        reserved=False,
        is_pet=False,
    ):
        self.sim_id = str(sim_id)
        self.household_id = str(household_id)
        self.age = str(age)
        self.pregnant = bool(pregnant)
        self.valid = bool(valid)
        self.sold = bool(sold)
        self.reserved = bool(reserved)
        self.is_pet = bool(is_pet)


class BuyerContext:
    def __init__(
        self,
        buyer_id="mysterious_stranger",
        demand_multiplier=1.0,
        risk_multiplier=1.0,
    ):
        self.buyer_id = str(buyer_id)
        self.demand_multiplier = float(demand_multiplier)
        self.risk_multiplier = float(risk_multiplier)


class SaleCandidate:
    def __init__(
        self,
        sim_id,
        name,
        age,
        traits=(),
        skills=(),
        fame_level=0,
        occults=(),
        career_level=0,
        education="none",
        expected_offspring=1,
    ):
        self.sim_id = str(sim_id)
        self.name = str(name)
        self.age = str(age)
        self.traits = tuple(traits)
        self.skills = tuple(skills)
        self.fame_level = int(fame_level or 0)
        self.occults = tuple(occults)
        self.career_level = int(career_level or 0)
        self.education = str(education)
        self.expected_offspring = max(1, int(expected_offspring or 1))


class SaleOffer:
    def __init__(self, amount, breakdown, buyer_id):
        self.amount = int(amount)
        self.breakdown = dict(breakdown)
        self.buyer_id = str(buyer_id)


class SaleTransaction:
    def __init__(self, transaction_type, actor_id, target_id, household_id):
        self.transaction_id = uuid.uuid4().hex
        self.transaction_type = str(transaction_type)
        self.actor_id = str(actor_id)
        self.target_id = str(target_id)
        self.household_id = str(household_id)
        self.state = "created"
        self.offer = None
        self.outcome = None
        self.payment_completed = False
        self.failure_reason = None
