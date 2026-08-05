from interactions.base.super_interaction import SuperInteraction
from interactions.rabbit_hole import HideSimLiability


class ShadySimDealsRabbitHoleInteraction(SuperInteraction):
    def on_added_to_queue(self, *args, **kwargs):
        liability = HideSimLiability(self)
        self.add_liability(liability.LIABILITY_TOKEN, liability)
        return super().on_added_to_queue(*args, **kwargs)
