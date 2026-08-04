# ShadySimDeals

ShadySimDeals is a darkly satirical The Sims 4 script mod. The playable household-sale workflow is available from phones and compatible computers.

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
7. Choose **Sell Household Member**.
8. Pick an eligible household member, review the offer, and confirm.

Eligible targets are household members from Teen through Elder. The active Sim, babies, infants, toddlers, children, pets, already-sold Sims, and Sims involved in another transaction are excluded.

The current offer is determined by age only. A completed sale transfers the target to a hidden **ShadySimDeals Holdings** household and then pays the active household. If payment fails, the transfer is rolled back.

Do not remove the mod while sold Sims remain in the holding household; recover them first or keep a backup of the save.

## Current scope

This release intentionally omits unborn-Nooboo sales, buffs, ghosts, delayed outcomes, and a real rabbit-hole animation. Those features remain isolated behind the existing domain services until their game APIs are verified. See [`SPECS_CHECKLIST.md`](SPECS_CHECKLIST.md) for detailed implementation status.

## Build and test

Requirements are Python 3.7 for game-compatible bytecode and Python 3.12 with `pytest` for development tests.

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests
py -3.12 build_mod.py
```

The build creates `dist/ShadySimDeals.ts4script` and `dist/ShadySimDeals.package`, including the English string table and Lot 51 phone/computer injection tuning.
