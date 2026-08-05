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
- [ ] Computer-use and phone-use animations
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
  - [ ] Live: child sale runs for 90 Sim minutes
  - [ ] Live: adult sale runs for 120 Sim minutes
  - [ ] Live: elder sale runs for 75 Sim minutes
  - [ ] Live: reloading an active sale makes no transfer or payment
- [x] Safe household transfer with rollback
  - [x] Live: sold child leaves the selectable household before payment
- [x] Exactly-once payment ordering
- [ ] Seller buffs
- [ ] Relationship consequences

### Phase 4: Unborn-Nooboo transaction

- [x] Pregnant-Sim picker implemented and unit-tested
- [x] Pregnancy adapter and safe pregnancy conclusion verified for patch `1.125.59.1030`
- [ ] Unborn rabbit hole
- [x] Multiple-offspring pricing connected to the public pregnancy tracker count
- [ ] Forced early twin/triplet detection
- [ ] Pregnant-Sim reaction

### Phase 5: Sold-Sim outcomes

- [x] Hidden ShadySimDeals Holdings household
- [x] Session-local sold-Sim registry
- [x] Same-session sold marker blocks repeat sales after external household restoration
- [ ] Save-slot-aware sold-Sim registry
- [ ] Explicit recovery command to return and unmark a deliberately restored sold Sim
- [ ] Ghost-return outcome
- [ ] Delayed events

### Phase 6: Release readiness

- [x] `.package` and `.ts4script` build
- [x] English localization resources
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
  - [ ] Live: newborn, infant, and toddler sales
- [x] 5. Unborn picker includes only pregnant household members, including the actor.
  - [x] Repository filtering and picker-row tests
  - [x] Live: pregnant active Sim appears
  - [x] Live: another pregnant household member appears
- [x] 6. A calculated offer appears before confirmation.
  - [x] Pregnant household-member offers bundle the configured unborn value
  - [x] Live: singleton pregnancy bonus and retained pregnancy
  - [ ] Live: twin and triplet household-member pregnancy bonuses
- [x] 7. Cancellation makes no changes.
- [ ] 8. Confirmation starts the appropriate rabbit hole.
  - [x] Automated: target age selects the 75-, 90-, or 120-minute shared tuning
  - [x] Package: `TwoSimRabbitHole` resources map Actor then PickedSim
  - [ ] Live: child, adult, and elder confirmations start shared rabbit holes
- [ ] 9. Household-member transactions return only the seller from a rabbit hole.
  - [x] Automated: target processing waits for the seller expiration callback
  - [x] Automated: cancellation makes no transfer or payment
  - [ ] Live: only the seller returns after child, adult, and elder sales
- [x] 10. Targets move out of the active household without hard deletion.
- [x] 11. Payment is deposited exactly once and only after target processing.
- [x] 12. Unborn transactions safely conclude the selected pregnancy.
  - [x] Public API adapter and compensated transaction tests
  - [x] Live: selected pregnancy concludes after a successful transaction
  - [ ] Live: active Sim pregnancy concludes with one payment
  - [ ] Live: other household member pregnancy concludes with one payment
- [ ] 13. Twins and triplets affect the live pregnancy offer.
  - [x] Pricing uses the public expected-offspring count
  - [ ] Live twin and triplet offers verified
- [ ] 14. Sellers receive trait-appropriate buffs.
- [ ] 15. Other selected pregnant Sims receive reaction buffs.
- [x] 16. Transactions validate and fail safely, including transfer rollback.
- [x] 17. Pricing and transaction logic have automated tests.
- [x] 18. The mod builds installable `.package` and `.ts4script` files.
- [x] 19. Current user-facing text uses localization resources.
- [x] 20. Build, installation, architecture, and usage documentation exists.
