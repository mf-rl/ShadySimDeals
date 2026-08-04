"""Configurable weighted target outcome selection."""

from . import config


class WeightedOutcomeSelector:
    def __init__(self, random_source, weights=None, allow_child_ghosts=False):
        self._random = random_source
        self._weights = dict(weights or config.OUTCOME_WEIGHTS)
        self._allow_child_ghosts = bool(allow_child_ghosts)

    def select(self, age):
        weights = dict(self._weights)
        if age in config.CHILD_AGES and not self._allow_child_ghosts:
            ghost_weight = weights.pop("ghost", 0)
            weights["hidden"] = weights.get("hidden", 0) + ghost_weight
        total = sum(max(0, value) for value in weights.values())
        if total <= 0:
            raise ValueError("At least one outcome weight must be positive")
        point = self._random.random() * total
        cumulative = 0
        for outcome, weight in weights.items():
            cumulative += max(0, weight)
            if point < cumulative:
                return outcome
        return next(reversed(weights))
