import importlib
import sys
from types import ModuleType


def test_queue_adds_native_hide_liability_before_native_handling(monkeypatch):
    events = []

    class FakeSuperInteraction:
        def add_liability(self, token, liability):
            events.append(("liability", token, liability))

        def on_added_to_queue(self, *args, **kwargs):
            events.append(("super", args, kwargs))
            return "queued"

    class FakeHideSimLiability:
        LIABILITY_TOKEN = "rabbit_hole"

        def __init__(self, interaction):
            self.interaction = interaction

    interactions = ModuleType("interactions")
    interactions.__path__ = []
    base = ModuleType("interactions.base")
    base.__path__ = []
    super_interaction = ModuleType("interactions.base.super_interaction")
    super_interaction.SuperInteraction = FakeSuperInteraction
    rabbit_hole = ModuleType("interactions.rabbit_hole")
    rabbit_hole.HideSimLiability = FakeHideSimLiability
    monkeypatch.setitem(sys.modules, "interactions", interactions)
    monkeypatch.setitem(sys.modules, "interactions.base", base)
    monkeypatch.setitem(
        sys.modules, "interactions.base.super_interaction", super_interaction
    )
    monkeypatch.setitem(sys.modules, "interactions.rabbit_hole", rabbit_hole)
    sys.modules.pop("shady_sim_deals.rabbit_hole_interaction", None)

    module = importlib.import_module("shady_sim_deals.rabbit_hole_interaction")
    interaction = module.ShadySimDealsRabbitHoleInteraction()

    assert interaction.on_added_to_queue(7, notify_client=False) == "queued"
    assert events[0][:2] == ("liability", "rabbit_hole")
    assert events[0][2].interaction is interaction
    assert events[1] == ("super", (7,), {"notify_client": False})
