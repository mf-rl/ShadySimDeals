from interactions.base.super_interaction import SuperInteraction
from interactions.rabbit_hole import HideSimLiability

from .logging import ModLogger


LOGGER = ModLogger()


class _LoggedHideSimLiability(HideSimLiability):
    def on_run(self):
        LOGGER.log("rabbit_hole_interaction_running")
        self._enter_native_rabbit_hole()
        return super().on_run()

    def _enter_native_rabbit_hole(self):
        import services

        rabbit_hole_id = self._interaction.interaction_parameters.get(
            "rabbit_hole_id"
        )
        if rabbit_hole_id is None:
            return
        sim_id = self._interaction.sim.sim_id
        service = services.get_rabbit_hole_service()
        rabbit_hole = service._get_rabbit_hole(sim_id, rabbit_hole_id)
        if (
            rabbit_hole is not None
            and sim_id not in rabbit_hole.get_all_sim_ids_in_rabbit_hole()
        ):
            service._on_sim_enter_rabbit_hole(sim_id, rabbit_hole_id)

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
