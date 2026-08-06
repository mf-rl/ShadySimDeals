# Session Progress — 2026-08-05

## Objective

Make every household-member and unborn-Nooboo transaction complete its rabbit
hole before changing household membership, pregnancy, or funds; replace
session-only sold flags with visible permanent traits and timed moodlets; and
verify the complete flow in The Sims 4 patch `1.125.59.1030`.

## Rabbit-hole transaction work

- Household-member sales now start one shared rabbit hole for the seller and
  target. Natural expiration returns the seller, moves the target to
  **ShadySimDeals Holdings**, and deposits payment afterward.
- Unborn sales now use a solo rabbit hole when the pregnant seller selects
  themself and a shared rabbit hole when another pregnant household member is
  selected. Pregnancy conclusion and payment occur only after natural
  expiration.
- Household durations remain 75 Sim minutes for elders, 90 for baby through
  child, and 120 for teen through adult. Unborn durations remain 90, 120, or
  150 Sim minutes for one, two, or three-or-more expected offspring.
- Invalid rabbit-hole liabilities and tuning that caused load errors were
  removed. The final implementation uses private non-saveable interactions,
  native rabbit-hole service expiration callbacks, and natural interaction
  release.
- Targets may transition to school or work without prematurely applying a
  sale. Transaction completion no longer depends on polling for a re-instanced
  target.

## Sale traits and moodlets

Successful transactions now apply these visible consequences:

| Recipient | Permanent trait | Timed moodlet |
| --- | --- | --- |
| Seller | **Family Asset Liquidator** | **Quarterly Profits, Fewer Mouths** — Happy, +4, 12 hours |
| Sold household member | **Outsourced by My Own Family** | **Apparently, Love Had a Return Policy** — Sad, +6, 24 hours |
| Other pregnant Sim whose unborn Nooboo was sold | **Stork Claim Mysteriously Denied** | **The Nursery Has Been Downsized** — Sad, +10, 48 hours |

- A pregnant seller targeting themself receives only the seller consequences.
- The permanent sold-state marker is the sold Sim's save-managed trait rather
  than process memory. Saving preserves it; exiting without saving restores the
  pre-sale trait state.
- Trait and Buff SimData resources were added to the package, eliminating the
  trait-selector UI exception.
- Trait SimData was updated to the current 184-byte client schema
  `0xC8782638`. All three traits now display their approved names,
  descriptions, icons, and shared **Shady Attribute** origin label.
- The implementation remains native and does not depend on WickedWhims or its
  custom trait type.

## Live-game verification

Verified successfully:

- Household sale: both Sims entered the rabbit hole; the target was removed
  afterward; payment was deposited; the seller moodlet and correctly named
  trait appeared; no exception was raised.
- Shared unborn sale: both Sims completed the rabbit hole; the selected
  pregnancy ended; payment was deposited; the appropriate moodlet and
  correctly named trait appeared.
- Exiting to the main menu without saving and reloading restored the pre-sale
  trait state as intended.

The first repeat household sale after that no-save reload failed with the
localized “inconvenient fact” notification. The mod log identified the precise
failure as `Source household no longer exists`. The household adapter was
caching the previous zone's household manager while SimInfo lookup used the
newly loaded zone. Commit `921d0f2` now fetches the current service manager
for each live transfer while preserving explicitly injected managers in tests.
A regression test reproduces the manager replacement and now passes.

## Verification and artifacts

- Current automated result: **117 passed**.
- `py -3.12 build_mod.py` builds both
  `dist/ShadySimDeals.package` and
  `dist/ShadySimDeals.ts4script`.
- `git diff --check` is clean.
- Commit `5d4912c` was installed and live-tested. The latest reload fix in
  `921d0f2` is built but still needs installation after the game is closed.

## Remaining live checks

1. Close the game, install the build containing `921d0f2`, complete a sale,
   exit to the main menu without saving, reload, and complete another household
   sale.
2. Measure every age-specific household duration and verify only the seller
   returns for each age band.
3. Verify the solo unborn path and all offspring-count durations.
4. Verify reload behavior during an active sale and the remaining newborn,
   infant, toddler, twin, and triplet cases in `SPECS_CHECKLIST.md`.

## Key commits

- `20e911b`–`97e1816`: route and package unborn rabbit holes.
- `a51b0d1`–`f4e87bb`: correct tuning, lifecycle, queue duration, hiding,
  and natural expiration behavior.
- `436131e`–`4fcea77`: package and apply permanent traits and moodlets.
- `d76555d`–`4ef1806`: use native trait/buff APIs, finish on expiration,
  allow school/work transitions, and package client data.
- `5d4912c`: name and categorize traits as **Shady Attribute**.
- `921d0f2`: refresh the household manager after a main-menu/save reload.

