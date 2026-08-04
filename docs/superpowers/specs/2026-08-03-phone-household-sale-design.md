# ShadySimDeals Phone Household Sale Design

## Goal

Deliver the first playable ShadySimDeals workflow for The Sims 4 patch
1.125.59.1030: a phone interaction that lets the active Sim sell a Teen through
Elder member of the active household without deleting the target SimInfo.

## Scope

This release includes one phone action, **Sell Household Member**. It uses
Lot51 Core 1.43 for phone affordance injection and native game dialogs for
selection, confirmation, and notifications.

This release does not expose unborn-Nooboo sales, computer interactions,
younger targets, timed rabbit holes, buffs, ghost returns, escapes, or
transaction reversals. Those features remain outside the live integration
until their game APIs and tuning contracts are independently verified.

## Architecture

Lot51 Core owns only the patch-sensitive phone affordance injection. All
filtering, pricing, transaction ordering, reservation, and payment rules remain
inside ShadySimDeals. The existing pure domain modules remain independent of
The Sims 4 and Lot51.

The runtime interaction performs five operations:

1. Generate native Sim-picker rows from the active household.
2. Revalidate the selected SimInfo and calculate an offer.
3. Show a localized confirmation dialog.
4. Transfer the target to a hidden holding household.
5. Deposit payment only after the transfer is verified.

Version-sensitive calls are isolated in `sims4_adapters.py`. The runtime class
in `sims4_runtime.py` coordinates dialogs and delegates domain work rather than
duplicating it.

## Candidate Rules

The picker reads SimInfo records from the active household. A candidate must:

- Exist and still belong to the active household.
- Be different from the active Sim.
- Be Teen, Young Adult, Adult, or Elder.
- Be human rather than a pet.
- Not be marked sold.
- Not be reserved by an active ShadySimDeals transaction.

The same rules run again after selection and immediately before transfer.

## Pricing

The live adapter creates a `SaleCandidate` from the selected SimInfo and uses
`SimSalePricingService`. This first integration supplies verified age data and
uses demand and risk multipliers of `1.0`.

Trait, skill, fame, career, education, and occult modifiers remain inactive in
the live adapter because their stable tuning-ID extraction has not yet been
verified. The existing domain pricing support and tests remain unchanged.

## User Flow

Lot51 injects **Sell Household Member** into a dedicated **ShadySimDeals** phone
category. The category is packaged as a matching PieMenuCategory XML and
SimData pair so both the simulation and phone client can resolve it. It reuses
an existing EA phone icon for this release.

Selecting the action always opens a native Sim picker. When no Teen-through-
Elder household member is eligible, the picker has no rows and can only be
closed; an empty result is not treated as an error.

After a target is selected, a native confirmation dialog displays the target
name and offer. **Suddenly Develop Morals** cancels without reserving Sims or
changing the save. **Complete Deal** begins the transaction.

The phone interaction remains queued while the target fades out and is
transferred. This is the safe presentation for the first release; it does not
pretend to use an unverified timed rabbit-hole API.

On success, a localized notification reports the payment. Notifications are
created through a fully tuned dialog factory rather than by directly
constructing `UiDialogNotification`, which omits required suppression tuning on
patch 1.125. On failure, a localized failure notification is shown and the log
records the failing stage.

## Holding Household

Before target mutation, the household adapter finds or creates one hidden,
unplayed household named **ShadySimDeals Holdings**. The household has no home
zone and receives no transaction funds.

The transfer uses EA's current household methods rather than modifying private
SimInfo fields directly. The adapter removes the SimInfo from the source and
adds it to the holding household through `add_sim_info_to_household`, then
verifies both household memberships.

The target SimInfo, genealogy, and relationships are preserved. The holding
household persists with the save. Removing the mod does not restore held Sims,
so the existing uninstall warning remains mandatory.

## Transaction and Failure Ordering

The runtime uses the existing transaction state machine and orchestrator.
Reservations cover both actor and target and are released in every terminal
path.

The mutation order is:

1. Validate actor, target, household, funds, and game shutdown state.
2. Reserve actor and target.
3. Create or resolve the holding household.
4. Fade the target and transfer its SimInfo.
5. Verify the target is absent from the source and present in holdings.
6. Deposit the offer exactly once.
7. Mark the transaction completed and notify the player.

If transfer fails, no payment occurs. If payment fails after transfer, the
adapter attempts to return the target to the source household and verifies the
rollback. Any rollback failure is logged prominently and reported as a failed
transaction without attempting further mutations.

## Localization and Packaging

All visible text uses stable string IDs. The English STBL is included in the
package rather than left as an external JSON import step.

The package contains:

- The phone interaction tuning.
- Its custom pie-menu category XML and matching SimData resource.
- The Lot51 tuning-injector snippet.
- The ENG_US string table.

The `.ts4script` contains Python 3.7 bytecode for ShadySimDeals only. Lot51 Core
1.43 or newer is a required separate installation and is not redistributed.

## Testing

Host-side tests cover:

- Teen through Elder inclusion and younger-age exclusion.
- Actor, pet, sold, invalid, and reserved exclusions.
- Runtime candidate-to-offer construction using age-only verified data.
- Empty candidate sets still opening a zero-row picker.
- Confirmation cancellation causing no reservation or mutation.
- Transfer verification before payment.
- Transfer failure preventing payment.
- Payment failure invoking transfer rollback.
- Lot51 injector resource presence in the built package.
- Matching custom category XML and SimData resources in the built package.
- ENG_US STBL presence in the built package.

The test cycle follows red-green-refactor for each new behavior. The complete
host suite and build run before installation.

## Live Verification

The running game must be closed before installed artifacts are replaced. After
restarting patch 1.125.59.1030 with script mods enabled and Lot51 Core 1.43
installed, verification covers:

1. No `lastException.txt` is generated during load.
2. The log confirms phone injection.
3. The phone shows the ShadySimDeals action.
4. The picker contains only eligible household members.
5. Cancellation changes neither household membership nor funds.
6. Confirmation moves the target and deposits the displayed amount once.
7. Saving and reloading preserves the target in the holding household.

Live verification uses a disposable test save. No memory writes or runtime
process patching are part of the design.
