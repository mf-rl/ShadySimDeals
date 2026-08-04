# Native Household Transfer and Computer Screen Design

## Goal

Ensure sold household members leave the active household and selectable portrait panel before payment, and show the native browsing display while ShadySimDeals computer interactions animate.

## Root Causes

Sims4HouseholdAdapter directly removes and adds SimInfo objects between household lists. The game-provided HouseholdManager.switch_sim_from_household_to_target_household method performs the same move plus active-client portrait updates, travel-group handling, daycare handling, career cleanup, and instantiated-Sim cleanup. Bypassing it leaves younger Sims selectable even though immediate list membership appears changed.

The computer interactions reuse the base-game browse animation and mixers but omit the base interaction's screen state extras. Base-game computer_Browse_Web sets screen value 15103 immediately and restores value 15106 at the end, including cancellation or exceptions.

## Design

Use switch_sim_from_household_to_target_household for both forward transfer and rollback. Pass destroy_if_empty_household=False and HouseholdChangeOrigin.UNKNOWN. Treat a false return value or incorrect resulting household membership as a failed transfer so the orchestrator cannot deposit payment.

Retain the existing holding-household lookup and transaction bookkeeping. Do not add manual portrait manipulation or custom child-specific logic.

Add the two verified state-change extras to both computer interaction resources. The display turns on before the five-second native computer-use sequence and returns to its normal end state even when the interaction is cancelled or raises.

## Verification

- Unit-test that forward transfer and rollback delegate to the native manager API and reject a false result.
- Preserve membership and rollback regression tests.
- Package-test both computer interactions for screen values 15103 and 15106 with the verified timings.
- Run the full suite and rebuild.
- Live-test a child sale for portrait removal and exactly one payment.
- Live-test both computer actions for a visible screen during animation.
