# Scripted Rabbit-Hole Liability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Load all six sale rabbit-hole interactions without tuning errors while preserving native routing, hiding, return, and expiration behavior.

**Architecture:** A single `SuperInteraction` subclass installs the native `HideSimLiability` when queued. The six XML affordances reference that subclass and stop tuning the liability through unsupported XML-only custom resources.

**Tech Stack:** Python 3.7 Sims 4 script API, XML tuning, pytest, DBPF package builder.

## Global Constraints

- Keep existing `Spawn_Arrival` constraints, `rabbit_hole_based` durations, participant mappings, and natural exit actions unchanged.
- Use the game's native `HideSimLiability`; do not implement custom hiding or restoration state.
- Preserve the existing rabbit-hole service expiration callback as the only trigger for sale application and payment.
- Support Python 3.7 syntax.

---

### Task 1: Scripted rabbit-hole interaction

**Files:**
- Create: `src/shady_sim_deals/rabbit_hole_interaction.py`
- Create: `tests/test_rabbit_hole_interaction.py`
- Modify: `tuning/interactions/household_rabbit_hole_75.xml`
- Modify: `tuning/interactions/household_rabbit_hole_90.xml`
- Modify: `tuning/interactions/household_rabbit_hole_120.xml`
- Modify: `tuning/interactions/unborn_rabbit_hole_90.xml`
- Modify: `tuning/interactions/unborn_rabbit_hole_120.xml`
- Modify: `tuning/interactions/unborn_rabbit_hole_150.xml`
- Modify: `tests/test_build.py`

**Interfaces:**
- Consumes: `interactions.base.super_interaction.SuperInteraction`, `interactions.rabbit_hole.HideSimLiability`.
- Produces: `shady_sim_deals.rabbit_hole_interaction.ShadySimDealsRabbitHoleInteraction.on_added_to_queue(*args, **kwargs)` with the native return value.

- [ ] **Step 1: Write the failing lifecycle test**

Create `tests/test_rabbit_hole_interaction.py` with fake Sims 4 modules. Import the production module only after installing those modules, instantiate the subclass, and assert its observed event order is `[("liability", "rabbit_hole", instance), ("super", args, kwargs)]`, the liability holds the interaction, and the return value from native queue handling is preserved.

```python
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
```

- [ ] **Step 2: Run the lifecycle test and verify RED**

Run: `$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_rabbit_hole_interaction.py`

Expected: FAIL because `shady_sim_deals.rabbit_hole_interaction` does not exist.

- [ ] **Step 3: Write the failing package-boundary assertions**

In both rabbit-hole loops in `tests/test_build.py`, replace the liability-key assertions with:

```python
assert interaction.attrib["c"] == "ShadySimDealsRabbitHoleInteraction"
assert interaction.attrib["m"] == "shady_sim_deals.rabbit_hole_interaction"
assert interaction.find("./L[@n='basic_liabilities']") is None
```

- [ ] **Step 4: Run package tests and verify RED**

Run: `$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_build.py`

Expected: FAIL because the XML still references `SuperInteraction` and contains `basic_liabilities`.

- [ ] **Step 5: Implement the minimal subclass**

Create `src/shady_sim_deals/rabbit_hole_interaction.py`:

```python
from interactions.base.super_interaction import SuperInteraction
from interactions.rabbit_hole import HideSimLiability


class ShadySimDealsRabbitHoleInteraction(SuperInteraction):
    def on_added_to_queue(self, *args, **kwargs):
        liability = HideSimLiability(self)
        self.add_liability(liability.LIABILITY_TOKEN, liability)
        return super().on_added_to_queue(*args, **kwargs)
```

- [ ] **Step 6: Point all six XML interactions at the subclass**

For each listed XML file, change the root attributes from:

```xml
c="SuperInteraction" m="interactions.base.super_interaction"
```

to:

```xml
c="ShadySimDealsRabbitHoleInteraction" m="shady_sim_deals.rabbit_hole_interaction"
```

Delete the complete `<L n="basic_liabilities">...</L>` element. Do not alter other tuning.

- [ ] **Step 7: Run focused tests and verify GREEN**

Run: `$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_rabbit_hole_interaction.py tests/test_build.py`

Expected: `14 passed`.

- [ ] **Step 8: Commit the implementation**

```powershell
git add src/shady_sim_deals/rabbit_hole_interaction.py tests/test_rabbit_hole_interaction.py tests/test_build.py tuning/interactions
git commit -m "fix: script rabbit hole hide liability"
```

### Task 2: Verify and install

**Files:**
- Generated: `dist/ShadySimDeals.ts4script`
- Generated: `dist/ShadySimDeals.package`

**Interfaces:**
- Consumes: Task 1 source and tuning.
- Produces: installed test artifacts under `Documents/Electronic Arts/The Sims 4/Mods/ShadySimDeals`.

- [ ] **Step 1: Run complete verification**

Run: `$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests`

Expected: all tests pass.

- [ ] **Step 2: Build the mod**

Run: `py -3.12 build_mod.py`

Expected: both distribution artifacts are built and the new module is present in `ShadySimDeals.ts4script`.

- [ ] **Step 3: Install and compare hashes**

Run: `.\install_mod.ps1`, then compare SHA-256 hashes for both built and installed artifacts.

Expected: package hashes match and script hashes match.

- [ ] **Step 4: Push the implementation commit**

Run: `git push`

Expected: the existing pull request branch updates successfully.

- [ ] **Step 5: Perform in-game verification**

Launch the game and verify no `interaction.py:2339` exception is generated. Then test household and unborn sales against the approved behavior before merging.
