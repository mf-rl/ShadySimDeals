# Development

## Verified baseline

- Game patch: `1.125.59.1030`.
- Dependency: Lot 51 Core Library 1.43 or newer.
- The game-side script is compiled with Python 3.7.
- A `.ts4script` is an uncompressed ZIP containing `.pyc` modules.
- Interaction tuning uses resource type `0xE882D22F`.
- Lot 51's `TuningInjector` injects the phone affordance into Sim object tuning `14965` through `phone_affordances`.
- Lot 51's `inject_by_object_tags` injects the computer affordance into objects tagged `Func_Computer` through their normal `affordances` list.
- The package contains phone and computer interactions for household-member and unborn-Nooboo sales, the injector snippet, the custom category XML and SimData, and ENG_US STBL resources.
- Patch `1.125.59.1030` exposes pregnancy state through `SimInfo.pregnancy_tracker.is_pregnant`, expected offspring through `offspring_count`, and safe conclusion through `clear_pregnancy()`.
- Device tuning was extracted with `ssinakhot/sims4-workspace` commit `15b984081907ad6961839db47a31331d749de294`.
- Phone device use derives from `phone_BrowseWebsites` (`13782`), `Phone_Browse` (`11701`), cellphone prop definition `62464`, and compatibility filter `76418`.
- Computer device use derives from `computer_Browse_Web` (`13187`), `Computer_Use_Type` (`31395`), mixers `13188`, `13189`, and `99858`, compatibility filter `77330`, and broken-state value `15080`.
- Shared household sales use `RabbitHoleService.put_sims_in_shared_rabbithole` and `set_rabbit_hole_expiration_callback` with `rabbit_hole.multi_sim_rabbit_hole.TwoSimRabbitHole`.
- Unborn sales use the same shared service for two Sims and `put_sim_in_managed_rabbithole` with `rabbit_hole.rabbit_hole.RabbitHole` when the pregnant seller targets themself.
- Rabbit-hole tuning uses resource type `0xB16AD2FA`, generic rabbit-hole animation factory `23834`, household rabbit-hole IDs `0xEAA21FFB1081E005`-`007`, unborn rabbit-hole IDs `0xEAA21FFB1081E00B`-`010`, and private affordance IDs `0xEAA21FFB1081E008`-`00A` and `011`-`013`.
- Managed rabbit-hole affordances route to `Spawn_Arrival`, use `rabbit_hole_based` duration conditions, and combine `fade_sim_out` with a `hide_sim_liability`. The similarly named `rabbit_hole` liability variant is not registered on patch `1.125.59.1030`.
- Permanent sale markers use save-managed gameplay trait tuning (`0xCB5FDDC7`); timed Happy and Sad consequences use buff tuning (`0x6017E896`).

Run tests with `py -3.12 -m pytest -q -p no:cacheprovider tests`. Build with `py -3.12 build_mod.py`; the build invokes Python 3.7 for game bytecode.

## Live verification checklist

After every supported game patch:

1. Confirm Lot 51 Core loads before ShadySimDeals and reports version 1.43 or newer.
2. Confirm **Sell Household Member** appears directly on the phone.
3. Click a compatible computer and confirm **ShadySimDeals > Sell Household Member** appears.
4. Confirm both entry points open the same picker and offer flow.
5. Confirm the picker includes baby-through-elder household members and excludes the active Sim.
6. Confirm cancelling the picker and confirmation dialog changes nothing.
7. Complete child, adult, and elder sales and measure 90, 120, and 75 Sim minutes respectively.
8. Confirm the seller and target enter the same rabbit hole, then only the seller returns.
9. Confirm natural expiration moves the target to **ShadySimDeals Holdings** and pays exactly once afterward.
10. Cancel an active household-sale rabbit hole and confirm no transfer or payment occurs.
11. Save and reload during an active sale and confirm it does not transfer the target or pay without a callback.
12. Confirm saving, reloading, and travelling preserve a completed sold Sim.
13. Confirm **Sell Unborn Nooboo** appears from both the phone and a compatible computer.
14. With the active Sim pregnant, confirm the unborn picker includes the actor and excludes non-pregnant household members.
15. With another household member pregnant, confirm the same picker includes that Sim.
16. Confirm cancellation leaves pregnancy and funds unchanged.
17. Select the pregnant active Sim; confirm that Sim enters alone, returns after the expected duration, then loses the pregnancy and receives exactly one payment.
18. Select another pregnant household member; confirm both Sims enter and return, then the target loses the pregnancy and the household receives exactly one payment.
19. Verify unborn durations of 90 Sim minutes for one expected offspring, 120 for twins, and 150 for triplets or more.
20. Cancel an active unborn-sale rabbit hole and confirm pregnancy and funds remain unchanged.
21. Confirm both phone actions visibly use the phone before their pickers.
22. Confirm both computer actions route to and visibly use a reachable computer before their pickers.
23. Confirm an inaccessible computer ends the interaction without opening a picker or changing game state.
24. Check `Documents\Electronic Arts\The Sims 4` for `lastException.txt` and review `ShadySimDeals.log`.
25. Complete a household sale and confirm the seller receives **Family Asset Liquidator** and **Quarterly Profits, Fewer Mouths**, while the target receives **Outsourced by My Own Family** and **Apparently, Love Had a Return Policy**.
26. Sell another Sim's unborn Nooboo and confirm the seller receives seller consequences while the pregnant target receives **Stork Claim Mysteriously Denied** and **The Nursery Has Been Downsized**.
27. Have a pregnant seller target themself and confirm that Sim receives only the seller trait and moodlet.
28. Save after a completed sale and reload; confirm permanent traits remain and expired moodlets do not reappear.
29. Complete a sale, exit to the main menu without saving, reload the pre-sale save, and confirm none of the sale traits or moodlets remain.

Do not install or replace `.package` or `.ts4script` files while the game is running.

## Deferred work

Trait and moodlet presentation, forced early multiple-birth detection, and ghost/delayed outcomes still require patch-specific live verification. The unborn rabbit-hole service calls and tunings require live verification on the supported patch. Recheck the recorded native device, rabbit-hole, trait, and buff tuning after every supported patch. Keep discovered identifiers in `sims4_adapters.py` or tuning, rather than spreading game calls through the domain code.
