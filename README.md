<p align="center">
  <img src="assets/ShadySimDeals-Logo.svg" alt="ShadySimDeals" width=50%>
</p>

ShadySimDeals is a darkly satirical The Sims 4 script mod. Household-member and unborn-Nooboo sales are available from phones and compatible computers.

## Requirements

- The Sims 4 patch `1.125.59.1030` (the verified development patch).
- [Lot 51 Core Library](https://lot51.cc/core), version 1.43 or newer.
- Custom Content and Script Mods enabled in Game Options.

## Installation and use

1. Close The Sims 4.
2. Install Lot 51 Core Library 1.43 or newer.
3. Copy `ShadySimDeals.package` and `ShadySimDeals.ts4script` into `Documents\Electronic Arts\The Sims 4\Mods\ShadySimDeals`.
4. Delete `Documents\Electronic Arts\The Sims 4\localthumbcache.package`.
5. Start the game and load a household.
6. Open a Sim's phone, or click a compatible computer and open **ShadySimDeals**.
7. Choose **Liquidate a Family Asset** or **Monetize Future Family Growth**.
8. Phone actions briefly animate in place. Computer actions route the Sim to the clicked computer and briefly use it.
9. Pick an eligible household member, review the offer, and confirm.

Eligible targets are household members from newborn/baby through elder. The active Sim, pets, already-sold Sims, and Sims involved in another transaction are excluded.

The household-member offer starts with the target's age value. If the target is pregnant, the configured unborn value and multiple-offspring multiplier are added to the offer; the pregnancy remains with the transferred Sim. After confirmation, the seller and target enter one shared rabbit hole for 75 Sim minutes when selling an elder, 90 for baby through child, or 120 for teen through adult. Natural expiration returns only the seller, transfers the target to the hidden **ShadySimDeals Holdings** household, and then pays the active household. Cancellation or startup failure transfers nobody and pays nothing; if payment fails after transfer, the transfer is rolled back.

The unborn picker includes every eligible pregnant non-pet household member, including the active Sim. Its offer uses the pregnancy tracker's expected offspring count. After confirmation, the seller and selected pregnant Sim enter a rabbit hole for 90 Sim minutes for one expected offspring, 120 for twins, or 150 for triplets or more. If the seller is selected, that Sim enters alone. Natural expiration returns every participant, deposits one payment, and then clears the selected pregnancy. Cancellation or startup failure leaves both pregnancy and funds unchanged. Because the count API only reports the current expected count, the mod does not force early twin or triplet detection.

Successful sellers permanently receive **Family Asset Liquidator** plus the 12-hour **Quarterly Profits, Fewer Mouths** Happy moodlet. A sold household member permanently receives **Outsourced by My Own Family** plus the 24-hour **Apparently, Love Had a Return Policy** Sad moodlet. When another pregnant Sim's unborn Nooboo is sold, that Sim permanently receives **Stork Claim Mysteriously Denied** plus the 48-hour **The Nursery Has Been Downsized** Sad moodlet. A pregnant seller targeting themself receives only the seller consequences.

A sold household member loses 100 friendship with the seller. When another pregnant Sim's unborn Nooboo is sold, their current friendship selects a complicit, regretful, or betrayed reaction that changes friendship by +10, -25, or -75. A pregnant seller targeting themself receives no relationship change.

Do not remove the mod while sold Sims remain in the holding household; recover them first or keep a backup of the save.

The permanent traits are normal save-managed Sim traits: saving preserves them, while exiting without saving restores the prior save state. Finish or cancel an active sale before saving and reloading because active sale callbacks and reservations remain session-local, and private rabbit-hole interactions are not persisted across reloads.

## Current scope

This release intentionally omits ghosts, delayed outcomes, forced early multiple-birth detection, and wider relationship effects for relatives, witnesses, sentiments, and grudges. See [`SPECS_CHECKLIST.md`](SPECS_CHECKLIST.md) for detailed implementation status.

## Build and test

Requirements are Python 3.7 for game-compatible bytecode and Python 3.12 with `pytest` for development tests.

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests
py -3.12 build_mod.py
```

The build creates `dist/ShadySimDeals.ts4script` and `dist/ShadySimDeals.package`, including the English string table and Lot 51 phone/computer injection tuning.
