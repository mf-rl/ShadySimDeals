# Development

## Verified baseline

- Game patch: `1.125.59.1030`.
- Dependency: Lot 51 Core Library 1.43 or newer.
- The game-side script is compiled with Python 3.7.
- A `.ts4script` is an uncompressed ZIP containing `.pyc` modules.
- Interaction tuning uses resource type `0xE882D22F`.
- Lot 51's `TuningInjector` injects the phone affordance into Sim object tuning `14965` through `phone_affordances`.
- Lot 51's `inject_by_object_tags` injects the computer affordance into objects tagged `Func_Computer` through their normal `affordances` list.
- The package contains both household-sale interactions, the injector snippet, the custom category XML and SimData, and ENG_US STBL resources.

Run tests with `py -3.12 -m pytest -q -p no:cacheprovider tests`. Build with `py -3.12 build_mod.py`; the build invokes Python 3.7 for game bytecode.

## Live verification checklist

After every supported game patch:

1. Confirm Lot 51 Core loads before ShadySimDeals and reports version 1.43 or newer.
2. Confirm **Sell Household Member** appears directly on the phone.
3. Click a compatible computer and confirm **ShadySimDeals > Sell Household Member** appears.
4. Confirm both entry points open the same picker and offer flow.
5. Confirm the picker includes only Teen-through-Elder household members and excludes the active Sim.
6. Confirm cancelling the picker and confirmation dialog changes nothing.
7. Confirm a completed sale moves the target to **ShadySimDeals Holdings** and pays exactly once.
8. Confirm saving, reloading, and travelling preserve the sold Sim.
9. Check `Documents\Electronic Arts\The Sims 4` for `lastException.txt` and review `ShadySimDeals.log`.

Do not install or replace `.package` or `.ts4script` files while the game is running.

## Deferred work

Unborn-Nooboo sales, native phone/computer animations, rabbit holes, buffs, persistence, pregnancy completion, and ghost/delayed outcomes still require patch-specific verification. Keep discovered identifiers in `sims4_adapters.py` or tuning, rather than spreading game calls through the domain code.
