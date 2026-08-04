"""Priority-based seller and pregnant-Sim reaction selection."""


class SellerReactionService:
    def select(self, traits, transaction_type, amount, expected_amount):
        traits = frozenset(traits)
        if "good" in traits or "family_oriented" in traits:
            return "sudden_attack_of_conscience"
        if amount < expected_amount * 0.75:
            return "sold_below_market_value"
        if amount >= expected_amount * 1.5:
            return "worth_every_relative"
        if transaction_type == "unborn":
            return "nooboo_futures_are_up"
        if "evil" in traits or "materialistic" in traits:
            return "household_is_finally_profitable"
        return "questionably_good_business"


class PregnantSimReactionService:
    DISTRIBUTIONS = (
        (50, (("complicit", 40), ("regretful", 35), ("betrayed", 25))),
        (0, (("complicit", 20), ("regretful", 40), ("betrayed", 40))),
        (-101, (("complicit", 10), ("regretful", 25), ("betrayed", 65))),
    )

    def __init__(self, random_source):
        self._random = random_source

    def select(self, relationship_score):
        distribution = self.DISTRIBUTIONS[-1][1]
        for threshold, candidate in self.DISTRIBUTIONS:
            if relationship_score >= threshold:
                distribution = candidate
                break
        point = self._random.random() * 100
        cumulative = 0
        for reaction, weight in distribution:
            cumulative += weight
            if point < cumulative:
                return reaction
        return distribution[-1][0]
