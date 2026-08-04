# Device-Use Animations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Play a brief native phone or computer-use sequence before every ShadySimDeals picker while preserving the existing sale workflows.

**Architecture:** The shared Python interaction base delegates to the normal `SuperInteraction` generator, applies the approved device-specific failure policy, and then calls the existing sale-type picker hook. The four interaction XML resources use minimal tuning derived from verified base-game phone and computer interactions on patch `1.125.59.1030`.

**Tech Stack:** Python 3.7-compatible Sims 4 scripts, pytest on Python 3.12, Sims 4 interaction XML, DBPF packaging, Lot51 Core 1.43+

## Global Constraints

- Supported game patch is `1.125.59.1030`.
- Game-side Python must remain compatible with Python 3.7.
- Lot51 Core 1.43 or newer remains the only mod dependency.
- Phone animation failure logs and falls back to the picker.
- Computer routing, posture, or animation failure ends without opening the picker.
- Device use happens before target selection and makes no transaction mutation.
- Do not add an artificial delay, rabbit hole, custom animation asset, or guessed tuning ID.
- Preserve the four existing interaction instance IDs and Lot51 injection references.

---

### Task 1: Sequence native device content before pickers

**Files:**
- Modify: `src/shady_sim_deals/sims4_runtime.py:143-496`
- Test: `tests/test_runtime.py`

**Interfaces:**
- Consumes: `SuperInteraction._run_interaction_gen(timeline)` and the existing household/unborn picker implementations.
- Produces: `_ShadySimDealsInteraction._run_interaction_gen(timeline)`, `_HouseholdMemberSaleInteraction._open_picker()`, `_UnbornSaleInteraction._open_picker()`, and `continue_after_device_failure: bool` on concrete device classes.

- [ ] **Step 1: Add a generator result helper and failing sequencing tests**

Add this test helper near the existing fakes in `tests/test_runtime.py`:

```python
def run_generator(generator):
    while True:
        try:
            next(generator)
        except StopIteration as stop:
            return stop.value
```

Add tests that replace the fallback parent runner and the picker hook:

```python
def test_device_content_finishes_before_picker(monkeypatch):
    events = []

    def run_device(self, timeline):
        events.append("device")
        yield from ()
        return True

    monkeypatch.setattr(
        sims4_runtime.SuperInteraction, "_run_interaction_gen", run_device
    )
    interaction = object.__new__(
        sims4_runtime.PhoneSellHouseholdMemberInteraction
    )
    interaction._open_picker = lambda: events.append("picker") or True

    assert run_generator(interaction._run_interaction_gen(None)) is True
    assert events == ["device", "picker"]


def test_phone_device_exception_logs_and_opens_picker(monkeypatch):
    events = []

    def fail_device(self, timeline):
        yield from ()
        raise RuntimeError("animation failed")

    monkeypatch.setattr(
        sims4_runtime.SuperInteraction, "_run_interaction_gen", fail_device
    )
    monkeypatch.setattr(
        sims4_runtime.LOGGER,
        "exception",
        lambda event, **data: events.append((event, data)),
    )
    interaction = object.__new__(sims4_runtime.PhoneSellUnbornNoobooInteraction)
    interaction._open_picker = lambda: events.append("picker") or True

    assert run_generator(interaction._run_interaction_gen(None)) is True
    assert events[-1] == "picker"
    assert events[0][0] == "device_animation_failed"
    assert events[0][1]["entry_point"] == "phone"


def test_computer_device_failure_suppresses_picker(monkeypatch):
    events = []

    def fail_device(self, timeline):
        yield from ()
        return False

    monkeypatch.setattr(
        sims4_runtime.SuperInteraction, "_run_interaction_gen", fail_device
    )
    monkeypatch.setattr(
        sims4_runtime.LOGGER,
        "log",
        lambda event, **data: events.append((event, data)),
    )
    interaction = object.__new__(
        sims4_runtime.ComputerSellHouseholdMemberInteraction
    )
    interaction._open_picker = lambda: events.append("picker") or True

    assert run_generator(interaction._run_interaction_gen(None)) is False
    assert "picker" not in events
    assert events == [
        ("device_animation_failed", {"entry_point": "computer"})
    ]
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_runtime.py -k "device_content or device_exception or device_failure"
```

Expected: failures because the fallback `SuperInteraction` has no native runner and the sale classes still open pickers directly.

- [ ] **Step 3: Add the shared device runner and picker hooks**

Give the ImportError fallback class a successful generator so unit tests model the native parent contract:

```python
class SuperInteraction:
    def _run_interaction_gen(self, timeline):
        yield from ()
        return True
```

Replace `_ShadySimDealsInteraction._run_interaction_gen` with:

```python
continue_after_device_failure = False

def _run_interaction_gen(self, timeline):
    try:
        device_succeeded = yield from super()._run_interaction_gen(timeline)
    except Exception:
        LOGGER.exception(
            "device_animation_failed", entry_point=self.entry_point
        )
        if not self.continue_after_device_failure:
            return False
    else:
        if device_succeeded is False:
            LOGGER.log(
                "device_animation_failed", entry_point=self.entry_point
            )
            if not self.continue_after_device_failure:
                return False
    return self._open_picker()
```

Rename the current `_run_interaction_gen` method on each sale-type base to `_open_picker`, remove its leading `yield from ()`, and leave its picker body and return values unchanged.

Set the concrete policies without duplicating behavior:

```python
class PhoneSellHouseholdMemberInteraction(_HouseholdMemberSaleInteraction):
    entry_point = "phone"
    continue_after_device_failure = True


class PhoneSellUnbornNoobooInteraction(_UnbornSaleInteraction):
    entry_point = "phone"
    continue_after_device_failure = True


class ComputerSellHouseholdMemberInteraction(_HouseholdMemberSaleInteraction):
    entry_point = "computer"


class ComputerSellUnbornNoobooInteraction(_UnbornSaleInteraction):
    entry_point = "computer"
```

- [ ] **Step 4: Run runtime and full tests**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_runtime.py
py -3.12 -m pytest -q -p no:cacheprovider tests
```

Expected: all tests pass; the existing picker tests exercise the successful fallback parent runner.

- [ ] **Step 5: Commit the runtime sequence**

```powershell
git add src/shady_sim_deals/sims4_runtime.py tests/test_runtime.py
git commit -m "feat: sequence device use before pickers"
```

---

### Task 2: Add verified phone and computer tuning

**Files:**
- Modify: `tuning/interactions/phone_sell_household_member.xml`
- Modify: `tuning/interactions/phone_sell_unborn_nooboo.xml`
- Modify: `tuning/interactions/computer_sell_household_member.xml`
- Modify: `tuning/interactions/computer_sell_unborn_nooboo.xml`
- Test: `tests/test_build.py`

**Interfaces:**
- Consumes: the normal `SuperInteraction` body enabled in Task 1.
- Produces: five-Sim-minute native phone browsing and computer browsing content before each picker.

**Verified patch sources:**

- `phone_BrowseWebsites`, instance `13782`.
- `Phone_Browse`, animation instance `11701`, ASM `Phone_Use`, state `BrowseActions`.
- Cellphone prop definition `62464`.
- `af_PhoneCompatability_TappingOnPhone`, instance `76418`.
- `computer_Browse_Web`, instance `13187`.
- `Computer_Use_Type`, animation instance `31395`, ASM `ComputerUse`, state `Type`.
- `Computer_Browse_Keyboard`, mixer instance `13188`.
- `Computer_Browse_Mouse`, mixer instance `13189`.
- `Computer_Use_React`, mixer instance `99858`.
- `af_ComputerCompatability`, instance `77330`.
- Native broken-computer state value `15080`.

- [ ] **Step 1: Add failing XML structure tests**

Add these helpers and tests to `tests/test_build.py`:

```python
def packaged_interactions():
    return {
        instance: ET.fromstring(data)
        for data, resource_type, _, instance in build_mod.package_resources()
        if resource_type == build_mod.INTERACTION_TUNING_TYPE
    }


def test_phone_sales_use_verified_phone_browse_content():
    interactions = packaged_interactions()
    for instance in (0xEAA1200000000001, 0xEAA21FFB1081E002):
        xml = interactions[instance]
        content = xml.find("./V[@n='basic_content']/U/V[@n='content']")
        timer = xml.find(
            "./V[@n='basic_content']/U/L[@n='conditional_actions']"
            "/V/U/L[@n='conditions']/V/U"
        )
        assert content.attrib["t"] == "looping_content"
        assert int(content.find("./U/U[@n='animation_ref']/T[@n='factory']").text) == 11701
        assert int(content.find(".//L[@n='props']/U/U[@n='value']/T[@n='definition']").text) == 62464
        assert (int(timer.find("./T[@n='min_time']").text), int(timer.find("./T[@n='max_time']").text)) == (5, 5)
        assert xml.find("./E[@n='target_type']").text == "ACTOR"
        assert int(xml.find("./V[@n='super_affordance_compatibility']/T").text) == 76418


def test_computer_sales_use_verified_computer_browse_content():
    interactions = packaged_interactions()
    for instance in (0xEAA21FFB1081E003, 0xEAA21FFB1081E004):
        xml = interactions[instance]
        content = xml.find("./V[@n='basic_content']/U/V[@n='content']")
        links = {int(node.text) for node in content.findall(".//L[@n='affordance_links']/T")}
        assert content.attrib["t"] == "staging_content"
        assert links == {13188, 13189, 99858}
        assert int(xml.find("./V[@n='canonical_animation']/U/T[@n='factory']").text) == 31395
        assert xml.find("./E[@n='target_type']").text == "OBJECT"
        assert int(xml.find("./V[@n='super_affordance_compatibility']/T").text) == 77330
        assert int(xml.find(".//V[@n='test_globals']/V/U/T[@n='value']").text) == 15080
```

- [ ] **Step 2: Run the build tests and verify RED**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_build.py -k "phone_sales_use or computer_sales_use"
```

Expected: failures because none of the four resources contains native device content.

- [ ] **Step 3: Add the minimal verified phone content to both phone XML files**

Keep each resource's existing class, name, instance, `_saveable`, `allow_autonomous`, and category. Add this identical content before the closing `</I>`:

```xml
  <L n="_constraints">
    <V t="circle"><U n="circle"><T n="require_los">False</T></U></V>
  </L>
  <V n="basic_content" t="flexible_length">
    <U n="flexible_length">
      <L n="conditional_actions">
        <V t="literal">
          <U n="literal">
            <L n="conditions">
              <V t="time_based"><U n="time_based"><T n="max_time">5</T><T n="min_time">5</T></U></V>
            </L>
            <E n="interaction_action">EXIT_NATURALLY</E>
          </U>
        </V>
      </L>
      <V n="content" t="looping_content">
        <U n="looping_content">
          <U n="animation_ref">
            <T n="factory">11701</T>
            <U n="overrides">
              <L n="props">
                <U><T n="key">cellphone</T><U n="value"><T n="definition">62464</T></U></U>
              </L>
            </U>
          </U>
        </U>
      </V>
    </U>
  </V>
  <U n="posture_preferences"><T n="find_best_posture">False</T></U>
  <V n="super_affordance_compatibility" t="reference"><T n="reference">76418</T></V>
  <E n="target_type">ACTOR</E>
```

- [ ] **Step 4: Add the minimal verified computer content to both computer XML files**

Keep each resource's existing identity and category. Add this identical content before the closing `</I>`:

```xml
  <V n="basic_content" t="flexible_length">
    <U n="flexible_length">
      <L n="conditional_actions">
        <V t="literal">
          <U n="literal">
            <L n="conditions">
              <V t="time_based"><U n="time_based"><T n="max_time">5</T><T n="min_time">5</T></U></V>
            </L>
            <E n="interaction_action">EXIT_NATURALLY</E>
          </U>
        </V>
      </L>
      <V n="content" t="staging_content">
        <U n="staging_content">
          <U n="content_set">
            <L n="affordance_links"><T>13189</T><T>13188</T><T>99858</T></L>
          </U>
        </U>
      </V>
    </U>
  </V>
  <V n="canonical_animation" t="enabled"><U n="enabled"><T n="factory">31395</T></U></V>
  <L n="interaction_category_tags"><E>Interaction_Computer</E><E>Interaction_Super</E><E>Interaction_All</E></L>
  <V n="super_affordance_compatibility" t="reference"><T n="reference">77330</T></V>
  <E n="target_type">OBJECT</E>
  <L n="test_globals">
    <V t="state"><U n="state"><E n="operator">NOTEQUAL</E><T n="value">15080</T></U></V>
  </L>
  <V n="utility_info" t="enabled"><L n="enabled"><E>POWER</E></L></V>
```

- [ ] **Step 5: Run focused and full tests**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_build.py
py -3.12 -m pytest -q -p no:cacheprovider tests
git diff --check
```

Expected: all tests pass and the diff check is clean.

- [ ] **Step 6: Commit the tuning**

```powershell
git add tests/test_build.py tuning/interactions
git commit -m "feat: add native device-use tuning"
```

---

### Task 3: Document, build, install, and verify in game

**Files:**
- Modify: `README.md`
- Modify: `DEVELOPMENT.md`
- Modify: `ARCHITECTURE.md`
- Modify: `SPECS_CHECKLIST.md`

**Interfaces:**
- Consumes: runtime and XML behavior from Tasks 1 and 2.
- Produces: compatibility evidence, player documentation, built artifacts, installation, and live verification status.

- [ ] **Step 1: Update documentation and checklist without claiming live success**

Document the following exact facts:

- `README.md`: phone actions briefly animate in place; computer actions route to and use the clicked computer before the picker.
- `DEVELOPMENT.md`: record extractor `ssinakhot/sims4-workspace` commit `15b984081907ad6961839db47a31331d749de294`; phone source `phone_BrowseWebsites` `13782`, animation `Phone_Browse` `11701`, prop `62464`, compatibility `76418`; computer source `computer_Browse_Web` `13187`, animation `Computer_Use_Type` `31395`, mixers `13188`, `13189`, `99858`, compatibility `77330`, broken state `15080`.
- `ARCHITECTURE.md`: native tuned device content runs through `SuperInteraction` before `_open_picker`; device failure policy differs by entry point.
- `SPECS_CHECKLIST.md`: add checked automated/package subitems under **Computer-use and phone-use animations**, but keep the parent and live phone/computer subitems unchecked.

- [ ] **Step 2: Run documentation checks and commit**

Run:

```powershell
rg -n "13782|11701|13187|31395|device|animation" README.md DEVELOPMENT.md ARCHITECTURE.md SPECS_CHECKLIST.md
git diff --check
```

Then commit:

```powershell
git add README.md DEVELOPMENT.md ARCHITECTURE.md SPECS_CHECKLIST.md
git commit -m "docs: describe native device-use animations"
```

- [ ] **Step 3: Run the final automated verification and build**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests
py -3.12 build_mod.py
Get-Item dist\ShadySimDeals.package, dist\ShadySimDeals.ts4script | Select-Object Name,Length,LastWriteTime
git status --short
```

Expected: all tests pass, both artifacts have fresh timestamps and nonzero sizes, and the worktree is clean.

- [ ] **Step 4: Install only while the game is closed**

Run:

```powershell
Get-Process TS4_x64 -ErrorAction SilentlyContinue
```

If the game is running, ask the user to close it and do not replace mod files. Once closed, run:

```powershell
.\install_mod.ps1
Start-Process -FilePath 'C:\Games\The Sims 4\Game\Bin\TS4_x64.exe'
```

- [ ] **Step 5: Ask the user to perform the live matrix**

Request these checks:

1. Phone **Sell Household Member** animates before its picker.
2. Phone **Sell Unborn Nooboo** animates before its picker.
3. A reachable computer routes and animates before each of its two pickers.
4. An inaccessible computer fails without a picker or mutation.
5. Picker cancellation changes nothing.
6. One household and one unborn transaction still complete correctly.

Inspect `lastException.txt` and the latest `shady_sim_deals.log` entries after the user responds.

- [ ] **Step 6: Record live verification only after evidence**

If every live check passes, mark the animation parent and its live phone/computer subitems checked in `SPECS_CHECKLIST.md`. Keep rabbit-hole acceptance criteria unchecked. Run `git diff --check`, then commit:

```powershell
git add SPECS_CHECKLIST.md
git commit -m "docs: record device animation live verification"
```

- [ ] **Step 7: Finish the branch**

Run a fresh full test suite, confirm `git status --short` is empty, then use `superpowers:finishing-a-development-branch`. This branch is stacked on `feature/unborn-sale`; if PR #2 has merged, target `master`, otherwise target `feature/unborn-sale`.
