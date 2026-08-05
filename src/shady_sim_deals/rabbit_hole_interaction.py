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

        sim_id = self._interaction.sim.sim_id
        service = services.get_rabbit_hole_service()
        rabbit_hole_id = service.get_head_rabbit_hole_id(sim_id)
        if rabbit_hole_id is None:
            return
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
    @classmethod
    def _tuning_loaded_callback(cls):
        cls.basic_liabilities = tuple(
            liability
            for liability in cls.basic_liabilities
            if not isinstance(liability, str)
        )
        return super()._tuning_loaded_callback()

    def on_added_to_queue(self, *args, **kwargs):
        liability = _LoggedHideSimLiability(self)
        self.add_liability(liability.LIABILITY_TOKEN, liability)
        self._prime_native_rabbit_hole_duration()
        return super().on_added_to_queue(*args, **kwargs)

    def _conditional_action_satisfied_callback(self, condition_group):
        import services

        rabbit_hole_id = self.interaction_parameters.get("rabbit_hole_id")
        if (
            rabbit_hole_id is not None
            and services.get_rabbit_hole_service().is_in_rabbit_hole(
                self.sim.sim_id, rabbit_hole_id
            )
        ):
            LOGGER.log("premature_rabbit_hole_exit_suppressed")
            return
        return super()._conditional_action_satisfied_callback(condition_group)

    def _prime_native_rabbit_hole_duration(self):
        import services

        sim_id = self.sim.sim_id
        service = services.get_rabbit_hole_service()
        rabbit_hole_id = service.get_head_rabbit_hole_id(sim_id)
        if rabbit_hole_id is None:
            return
        rabbit_hole = service._get_rabbit_hole(sim_id, rabbit_hole_id)
        if (
            rabbit_hole is not None
            and rabbit_hole.alarm_handle is None
            and rabbit_hole.time_remaining_on_load is None
        ):
            rabbit_hole.time_remaining_on_load = rabbit_hole._get_duration()
