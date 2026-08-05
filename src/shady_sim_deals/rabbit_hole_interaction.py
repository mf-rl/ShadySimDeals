from interactions.base.super_interaction import SuperInteraction
from interactions.rabbit_hole import HideSimLiability

from .logging import ModLogger


LOGGER = ModLogger()


class _LoggedHideSimLiability(HideSimLiability):
    def on_run(self):
        LOGGER.log("rabbit_hole_interaction_running")
        return super().on_run()

    def release(self):
        LOGGER.log(
            "rabbit_hole_interaction_releasing",
            finishing_naturally=bool(
                getattr(self._interaction, "is_finishing_naturally", False)
            ),
            finishing_type=str(
                getattr(self._interaction, "finishing_type", None)
            ),
        )
        return super().release()


class ShadySimDealsRabbitHoleInteraction(SuperInteraction):
    def on_added_to_queue(self, *args, **kwargs):
        liability = _LoggedHideSimLiability(self)
        self.add_liability(liability.LIABILITY_TOKEN, liability)
        return super().on_added_to_queue(*args, **kwargs)
