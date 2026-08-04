# Development

## Verified baseline

- Game patch: `1.125.59.1030`.
- Dependency: Lot 51 Core Library 1.43 or newer.
- The game-side script is compiled with Python 3.7.
- A `.ts4script` is an uncompressed ZIP containing `.pyc` modules.
- Interaction tuning uses resource type `0xE882D22F`.
- Lot 51's `TuningInjector` injects the phone affordance into Sim object tuning `14965` through `phone_affordances`.
- The package contains the interaction, injector snippet, and ENG_US STBL resources. The interaction is deliberately uncategorized because custom category UI metadata requires a matching SimData resource.

Run tests with `py -3.12 -m pytest -q -p no:cacheprovider tests`. Build with `py -3.12 build_mod.py`; the build invokes Python 3.7 for game bytecode.

## Live verification checklist

After every supported game patch:

1. Confirm Lot 51 Core loads before ShadySimDeals and reports version 1.43 or newer.
2. Confirm **Sell Household Member** appears directly on the phone.
3. Confirm the picker includes only Teen-through-Elder household members and excludes the active Sim.
4. Confirm cancelling the picker and confirmation dialog changes nothing.
5. Confirm a completed sale moves the target to **ShadySimDeals Holdings** and pays exactly once.
6. Confirm saving, reloading, and travelling preserve the sold Sim.
7. Check `Documents\Electronic Arts\The Sims 4` for `lastException.txt` and review `ShadySimDeals.log`.

Do not install or replace `.package` or `.ts4script` files while the game is running.

## Deferred work

Computer entry points, unborn-Nooboo sales, native phone animations, rabbit holes, buffs, persistence, pregnancy completion, and ghost/delayed outcomes still require patch-specific verification. Keep discovered identifiers in `sims4_adapters.py` or tuning, rather than spreading game calls through the domain code.
