# Native Transfer and Computer Screen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Remove sold Sims from the active household portrait through the native game lifecycle and display the native browsing screen during both computer sale interactions.

**Architecture:** Sims4HouseholdAdapter delegates forward and rollback moves to HouseholdManager.switch_sim_from_household_to_target_household and retains its existing membership verification. Both computer XML resources add the verified browse-screen start and end state changes around their existing five-second native animation.

**Tech Stack:** Python 3.7-compatible Sims 4 scripts, pytest on Python 3.12, Sims 4 interaction XML, DBPF packaging, Lot51 Core 1.43+

## Global Constraints

- Supported game patch is 1.125.59.1030.
- Game-side Python must remain compatible with Python 3.7.
- Lot51 Core 1.43 or newer remains the only mod dependency.
- Do not hard-delete Sims, genealogy, or bassinets.
- Do not deposit payment unless the native household switch succeeds and membership verification passes.
- Use base-game computer state values 15103 at start and 15106 at end.
- Restore the screen on cancellation or exception.

---

### Task 1: Use the native household switch lifecycle

**Files:**
- Modify: tests/test_sims4_adapters.py
- Modify: src/shady_sim_deals/sims4_adapters.py:144-202

**Interfaces:**
- Consumes: HouseholdManager.switch_sim_from_household_to_target_household(sim_info, starting_household, destination_household, destroy_if_empty_household, reason) -> bool.
- Produces: Sims4HouseholdAdapter transfers and rollbacks that update active-client selectable Sims through the native manager.

- [ ] **Step 1: Add native-switch behavior to the fake manager and failing assertions**

Add switch_calls and switch_result to FakeHouseholdManager. Its fake native method records all five arguments, returns False without mutation when switch_result is false, and otherwise performs the existing fake remove/add:

    def switch_sim_from_household_to_target_household(
        self,
        sim_info,
        starting_household,
        destination_household,
        destroy_if_empty_household=False,
        reason=None,
    ):
        self.switch_calls.append(
            (
                sim_info,
                starting_household,
                destination_household,
                destroy_if_empty_household,
                reason,
            )
        )
        if not self.switch_result:
            return False
        starting_household.remove_sim_info(
            sim_info,
            destroy_if_empty_household=destroy_if_empty_household,
            assign_to_none=False,
        )
        destination_household.add_sim_info_to_household(sim_info, reason=reason)
        return True

In test_household_adapter_moves_target_to_reused_hidden_holdings_and_rolls_back, assert two calls were made, first source-to-holdings and then holdings-to-source, both with destroy_if_empty_household false.

Inject a fake sims.household_enums module with HouseholdChangeOrigin.UNKNOWN for adapter tests.

Keep the existing holding-add failure setup and assertions. Because the fake native method removes from the source before the configured destination add raises, this proves exception recovery uses the native method in reverse. Add a separate test with switch_result=False and assert IntegrationUnavailable is raised while the target remains in the source.

- [ ] **Step 2: Run the adapter tests and verify failure**

Run:

    $env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_sims4_adapters.py

Expected: the native-switch assertions fail because the adapter still directly mutates household lists.

- [ ] **Step 3: Delegate forward and rollback moves to the native manager**

Inside both adapter methods, import HouseholdChangeOrigin from sims.household_enums and call:

    switched = manager.switch_sim_from_household_to_target_household(
        sim_info,
        source,
        holdings,
        destroy_if_empty_household=False,
        reason=HouseholdChangeOrigin.UNKNOWN,
    )

Use holdings and source in reverse order for rollback. Raise RuntimeError or IntegrationUnavailable when switched is false, then preserve the existing membership checks and transfer bookkeeping.

If the forward native call raises after membership changed, invoke the same native method from holdings back to source before raising IntegrationUnavailable. If that recovery also fails, retain both errors in the existing rollback-failed message. Remove only the direct remove_sim_info/add_sim_info calls; do not remove rollback safety.

- [ ] **Step 4: Run adapter and transaction tests**

Run:

    $env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_sims4_adapters.py tests/test_transactions.py tests/test_processors.py

Expected: all selected tests pass.

- [ ] **Step 5: Commit the transfer fix**

    git add src/shady_sim_deals/sims4_adapters.py tests/test_sims4_adapters.py
    git commit -m "fix: use native household transfer lifecycle"

### Task 2: Turn on the computer display during device use

**Files:**
- Modify: tests/test_build.py:93-115
- Modify: tuning/interactions/computer_sell_household_member.xml
- Modify: tuning/interactions/computer_sell_unborn_nooboo.xml

**Interfaces:**
- Consumes: base-game state values 15103 (browse display) and 15106 (end state).
- Produces: two packaged computer interactions with immediate-on and cancel-safe end-state extras.

- [ ] **Step 1: Add failing package assertions for screen state extras**

In test_computer_sales_use_verified_computer_browse_content, collect each state_change under ./L[@n='basic_extras'] and assert:

    state_changes = xml.findall("./L[@n='basic_extras']/V[@t='state_change']/U")
    assert [
        int(node.find(".//T[@n='new_value']").text)
        for node in state_changes
    ] == [15103, 15106]
    assert state_changes[0].find("./V[@n='timing']").attrib["t"] == "immediately"
    end_timing = state_changes[1].find("./V[@n='timing']")
    assert end_timing.attrib["t"] == "at_end"
    assert end_timing.find("./U/E[@n='criticality']").text == "OnCancelOrException"

- [ ] **Step 2: Run the package test and verify failure**

Run:

    $env:PYTHONPATH='.'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_build.py::test_computer_sales_use_verified_computer_browse_content

Expected: failure because both XML resources currently have no basic_extras list.

- [ ] **Step 3: Add the two native screen state changes to both XML files**

Add this list as a direct child of each interaction:

    <L n="basic_extras">
      <V t="state_change">
        <U n="state_change">
          <V n="new_value" t="single_value"><U n="single_value"><T n="new_value">15103</T></U></V>
          <V n="timing" t="immediately" />
        </U>
      </V>
      <V t="state_change">
        <U n="state_change">
          <V n="new_value" t="single_value"><U n="single_value"><T n="new_value">15106</T></U></V>
          <V n="timing" t="at_end"><U n="at_end"><E n="criticality">OnCancelOrException</E></U></V>
        </U>
      </V>
    </L>

- [ ] **Step 4: Run the package test and full suite**

Run:

    $env:PYTHONPATH='.'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_build.py::test_computer_sales_use_verified_computer_browse_content
    $env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests

Expected: all tests pass.

- [ ] **Step 5: Commit the display fix**

    git add tests/test_build.py tuning/interactions/computer_sell_household_member.xml tuning/interactions/computer_sell_unborn_nooboo.xml
    git commit -m "fix: show computer screen during device use"

### Task 3: Build, install, and live-verify

**Files:**
- Generated: dist/ShadySimDeals.package
- Generated: dist/ShadySimDeals.ts4script
- Modify after live confirmation: SPECS_CHECKLIST.md

**Interfaces:**
- Consumes: Tasks 1 and 2.
- Produces: installed artifacts and recorded live acceptance evidence.

- [ ] **Step 1: Build and verify fresh artifacts**

Run:

    py -3.12 build_mod.py

Expected: successful build of both files with fresh timestamps.

- [ ] **Step 2: Install only after The Sims 4 is closed**

Run:

    .\install_mod.ps1

Expected: installed file hashes match dist.

- [ ] **Step 3: Live-test both regressions**

Sell a child and verify the child disappears from the lower-left portrait panel before one payment is deposited. Run both computer sale actions and verify a visible browsing display appears during the animation and returns to the normal end state afterward.

- [ ] **Step 4: Record only confirmed evidence**

Update SPECS_CHECKLIST.md for the confirmed child support and computer animation/display behavior. Leave newborn, infant, toddler, and any untested failure-path criteria unchecked.

- [ ] **Step 5: Commit checklist evidence**

    git add SPECS_CHECKLIST.md
    git commit -m "docs: record transfer and screen verification"
