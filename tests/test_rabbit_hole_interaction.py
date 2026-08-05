import importlib
import sys
from types import ModuleType


def test_queue_adds_native_hide_liability_before_native_handling(monkeypatch):
    events = []

    class FakeSuperInteraction:
        def __init__(self):
            self.interaction_parameters = {"rabbit_hole_id": 999}
            self.sim = type("Sim", (), {"sim_id": 1})()

        def add_liability(self, token, liability):
            events.append(("liability", token, liability))

        def on_added_to_queue(self, *args, **kwargs):
            events.append(("super", args, kwargs))
            return "queued"

    class FakeHideSimLiability:
        LIABILITY_TOKEN = "rabbit_hole"

        def __init__(self, interaction):
            self.interaction = interaction
            self._interaction = interaction

        def on_run(self):
            events.append(("native_on_run",))

        def release(self):
            events.append(("native_release",))

    interactions = ModuleType("interactions")
    interactions.__path__ = []
    base = ModuleType("interactions.base")
    base.__path__ = []
    super_interaction = ModuleType("interactions.base.super_interaction")
    super_interaction.SuperInteraction = FakeSuperInteraction
    rabbit_hole = ModuleType("interactions.rabbit_hole")
    rabbit_hole.HideSimLiability = FakeHideSimLiability

    class FakeRabbitHole:
        alarm_handle = None
        time_remaining_on_load = None

        def _get_duration(self):
            events.append(("duration",))
            return "75 sim minutes"

        def get_all_sim_ids_in_rabbit_hole(self):
            return ()

    fake_rabbit_hole = FakeRabbitHole()

    class FakeRabbitHoleService:
        def get_head_rabbit_hole_id(self, sim_id):
            return 91

        def _get_rabbit_hole(self, sim_id, rabbit_hole_id):
            return fake_rabbit_hole

        def _on_sim_enter_rabbit_hole(self, sim_id, rabbit_hole_id):
            events.append(("service_enter", sim_id, rabbit_hole_id))

    services = ModuleType("services")
    services.get_rabbit_hole_service = lambda: FakeRabbitHoleService()
    monkeypatch.setitem(sys.modules, "interactions", interactions)
    monkeypatch.setitem(sys.modules, "interactions.base", base)
    monkeypatch.setitem(
        sys.modules, "interactions.base.super_interaction", super_interaction
    )
    monkeypatch.setitem(sys.modules, "interactions.rabbit_hole", rabbit_hole)
    monkeypatch.setitem(sys.modules, "services", services)
    sys.modules.pop("shady_sim_deals.rabbit_hole_interaction", None)

    module = importlib.import_module("shady_sim_deals.rabbit_hole_interaction")
    interaction = module.ShadySimDealsRabbitHoleInteraction()

    assert interaction.on_added_to_queue(7, notify_client=False) == "queued"
    assert events[0][:2] == ("liability", "rabbit_hole")
    assert events[0][2].interaction is interaction
    assert events[1] == ("duration",)
    assert events[2] == ("super", (7,), {"notify_client": False})
    assert fake_rabbit_hole.time_remaining_on_load == "75 sim minutes"

    class FakeLogger:
        def log(self, event, **fields):
            events.append((event, fields))

    module.LOGGER = FakeLogger()
    interaction.is_finishing_naturally = False
    interaction.finishing_type = "TRANSITION_FAILURE"
    liability = events[0][2]
    liability.on_run()
    liability.release()

    assert events[3] == ("rabbit_hole_interaction_running", {})
    assert events[4] == ("service_enter", 1, 91)
    assert events[5] == ("native_on_run",)
    assert events[6] == (
        "rabbit_hole_interaction_releasing",
        {
            "finishing_naturally": False,
            "finishing_type": "TRANSITION_FAILURE",
        },
    )
    assert events[7] == ("native_release",)
