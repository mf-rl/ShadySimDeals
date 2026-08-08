# ShadySimDeals Specification Checklist

This checklist tracks `SPECS.md`. Checked items are supported by repository code,
automated tests, or recorded in-game verification. Items requiring new game-side
verification remain unchecked.

## Implementation phases

### Phase 1: Core

- [x] Repository analysis and project skeleton
- [x] Logging and configuration
- [x] Shared transaction models and state machine
- [x] Pricing service and unit tests

### Phase 2: Entry points and dialogs

- [x] Phone household-sale injection
- [x] Computer household-sale injection packaged and unit-tested
- [x] Computer household-sale visibility verified in game
- [x] Shared native household picker and confirmation dialog
- [x] Phone and computer unborn-Nooboo entry points packaged and unit-tested
- [x] Phone and computer unborn-Nooboo visibility verified in game
- [x] Computer-use and phone-use animations
  - [x] Native phone/computer tuning packaged and unit-tested
  - [x] Device-first runtime order and failure policies unit-tested
  - [x] Live: both phone actions animate before the picker
  - [x] Live: both computer actions route and animate before the picker
  - [x] Live: computer screen is active during the animation
  - [x] Live: inaccessible computer fails without opening a picker

### Phase 3: Household-member transaction

- [x] Real rabbit-hole workflow and timed return
  - [x] Shared seller/target service adapter and expiration callback unit-tested
  - [x] Private 75-, 90-, and 120-minute rabbit-hole resources packaged and indexed
  - [x] Transfer and payment delayed until natural expiration; cancellation safety unit-tested
  - [x] Active private rabbit-hole interactions are non-saveable and package-tested
  - [x] Live: one household-member sale completed the shared rabbit hole before removal and payment
  - [x] Live: child sale runs for 90 Sim minutes
  - [x] Live: adult sale runs for 120 Sim minutes
  - [x] Live: elder sale runs for 75 Sim minutes
  - [ ] Live: reloading an active sale makes no transfer or payment
- [x] Safe household transfer with rollback
  - [x] Live: sold child leaves the selectable household before payment
- [x] Exactly-once payment ordering
- [x] Fixed seller trait and Happy moodlet
- [ ] Trait-aware seller reaction buffs wired to live consequences
- [x] Direct seller/target friendship consequences implemented and unit-tested
- [x] Wider close-relative and household-witness friendship consequences implemented and unit-tested
  - [x] Live: after selling a toddler, its mother loses 50 friendship with the seller
  - [ ] Live: household-only witness loses 25 and an overlapping relative receives one 50-point loss
- [ ] Observer reaction buffs, sentiments, and persistent grudges

### Phase 4: Unborn-Nooboo transaction

- [x] Pregnant-Sim picker implemented and unit-tested
  - [x] Automated: sale pickers exclude off-lot non-newborn Sims; the household picker retains uninstantiated newborns
  - [x] Live: Sims at work or school are absent from both sale pickers
- [x] Pregnancy adapter and safe pregnancy conclusion verified for patch `1.125.59.1030`
- [x] Unborn rabbit hole
  - [x] Automated: self-target uses a solo rabbit hole; another target uses a shared rabbit hole
  - [x] Automated: payment and pregnancy conclusion wait for natural expiration
  - [x] Package: private 90-, 120-, and 150-minute resources are indexed and non-saveable
  - [x] Live: pregnant seller enters alone and returns before pregnancy conclusion and payment
  - [x] Live: seller and another pregnant target both enter and return before pregnancy conclusion and payment
- [x] Multiple-offspring pricing connected to the public pregnancy tracker count
- [ ] Forced early twin/triplet detection
- [x] Fixed pregnant-target lost-unborn trait and Sad moodlet
- [ ] Outcome-specific complicit, regretful, and betrayed moodlets

### Phase 5: Sold-Sim outcomes

- [x] Hidden ShadySimDeals Holdings household
- [x] Permanent visible trait-backed sold-Sim registry
- [x] Same-session sold marker blocks repeat sales after external household restoration
- [x] Save-slot-aware sold marker through normal `SimInfo` trait persistence
- [x] Automated: household transfers refresh the service manager after a save reload
- [x] Live: household and unborn sales succeed after a no-save main-menu reload
- [ ] Explicit recovery command to return and unmark a deliberately restored sold Sim
- [ ] Ghost-return outcome
- [ ] Delayed events

### Phase 6: Release readiness

- [x] `.package` and `.ts4script` build
- [x] English localization resources
- [x] Custom app, pie-menu, queue, trait, and moodlet DST5 resources packaged and reference-tested
- [x] Source PNGs compile automatically during the normal build without checked-in generated textures
- [x] Live: custom icons render in phone/computer menus, the interaction queue, trait panels, and moodlet panels
- [x] Architecture, build, installation, and usage documentation
- [x] Automated regression suite
- [x] Computer interaction live compatibility check
- [ ] Full acceptance regression in the supported game patch

## Acceptance criteria

- [x] 1. ShadySimDeals appears on supported phones.
- [x] 2. ShadySimDeals appears on supported computers.
- [x] 3. Both entry points expose household-member and unborn-Nooboo sales.
- [ ] 4. Household picker supports every required age and excludes the actor.
  - [x] Actor exclusion and Teen-through-Elder filtering
  - [x] Baby, infant, toddler, and child filtering and pricing
  - [x] Live: child appears and completes a sale
  - [x] Live: infant sale completes after the seller carries the infant into the rabbit hole
  - [ ] Live: newborn appears and can be selected; the latest attempt stops after selection because seller reservation is rejected before Check On, and the synchronous failure leaves the newborn filtered from the next picker (next-tick handoff and transaction cleanup await validation)
  - [x] Live: toddler appears and completes a sale
  - [x] Automated: newborn and infant sales acquire carry ownership before a seller-only 90-minute rabbit hole
  - [x] Automated: newborn `SimInfo` resolves its matching `Baby` object before native Check On
  - [x] Automated: an existing newborn carrier completes a natural put-down, the seller waits one simulation tick before reserving it, then native Check On verifies persistent Held Actions; an existing infant carrier hands it to the seller
  - [x] Automated: the carried newborn or infant is not registered as a second rabbit-hole participant
  - [x] Live: another carrier hands the infant to the seller, who carries it into the rabbit hole
- [x] 5. Unborn picker includes only pregnant household members, including the actor.
  - [x] Repository filtering and picker-row tests
  - [x] Live: pregnant active Sim appears
  - [x] Live: another pregnant household member appears
- [x] 6. A calculated offer appears before confirmation.
  - [x] Pregnant household-member offers bundle the configured unborn value
  - [x] Live: singleton pregnancy bonus and retained pregnancy
  - [ ] Live: twin and triplet household-member pregnancy bonuses
- [x] 7. Cancellation makes no changes.
- [x] 8. Confirmation starts the appropriate rabbit hole.
  - [x] Automated: toddler-through-elder target age selects the 75-, 90-, or 120-minute shared household tuning
  - [x] Automated: newborn and infant sales use the private 90-minute solo tuning for the seller
  - [x] Automated: expected offspring selects the 90-, 120-, or 150-minute unborn tuning
  - [x] Package: shared `TwoSimRabbitHole` resources map Actor then PickedSim
  - [x] Package: self-target unborn resources use a solo `RabbitHole`
  - [x] Live: child, adult, and elder confirmations start shared rabbit holes
  - [x] Live: both unborn target paths start the expected rabbit hole
- [x] 9. Household-member transactions return only the seller from a rabbit hole.
  - [x] Automated: target processing waits for the seller expiration callback
  - [x] Automated: cancellation makes no transfer or payment
  - [x] Live: seller returns alone after the 90-minute infant sale and payment completes
  - [x] Live: only the seller returns after child, adult, and elder sales
- [x] 10. Targets move out of the active household without hard deletion.
- [x] 11. Payment is deposited exactly once and only after target processing.
- [x] 12. Unborn transactions safely conclude the selected pregnancy.
  - [x] Public API adapter and compensated transaction tests
  - [x] Live: selected pregnancy concludes after a successful transaction
  - [x] Live: active Sim pregnancy concludes with one payment
  - [x] Live: other household member pregnancy concludes with one payment
- [ ] 13. Twins and triplets affect the live pregnancy offer.
  - [x] Pricing uses the public expected-offspring count
  - [ ] Live twin and triplet offers verified
- [ ] 14. Sellers receive trait-appropriate buffs.
  - [x] Sellers receive the permanent trait and fixed Happy moodlet.
  - [x] Pure seller-reaction priority selection is unit-tested.
  - [ ] Live consequences select and apply tuned buffs from seller traits and sale context.
- [ ] 15. Another selected pregnant Sim receives a reaction buff.
  - [x] Other selected pregnant Sims receive the permanent trait and fixed Sad moodlet.
  - [x] Complicit, regretful, and betrayed outcomes drive the implemented relationship change.
  - [ ] The selected outcome drives a corresponding tuned reaction moodlet.
- [x] 16. Transactions validate and fail safely, including transfer rollback.
- [x] 17. Pricing and transaction logic have automated tests.
- [x] 18. The mod builds installable `.package` and `.ts4script` files.
- [x] 19. Current user-facing text uses localization resources.
- [x] 20. Build, installation, architecture, and usage documentation exists.
