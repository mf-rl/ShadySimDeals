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
- [ ] Phone and computer unborn-Nooboo entry points
- [ ] Computer-use and phone-use animations

### Phase 3: Household-member transaction

- [ ] Real rabbit-hole workflow and timed return
- [x] Safe household transfer with rollback
- [x] Exactly-once payment ordering
- [ ] Seller buffs
- [ ] Relationship consequences

### Phase 4: Unborn-Nooboo transaction

- [ ] Pregnant-Sim picker
- [ ] Verified pregnancy adapter and safe pregnancy conclusion
- [ ] Unborn rabbit hole
- [ ] Multiple-offspring pricing connected to game pregnancy data
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
- [ ] 3. Both entry points expose household-member and unborn-Nooboo sales.
- [ ] 4. Household picker supports every required age and excludes the actor.
  - [x] Actor exclusion and Teen-through-Elder filtering
  - [ ] Baby, infant, toddler, and child support
- [ ] 5. Unborn picker includes only pregnant household members, including the actor.
- [x] 6. A calculated offer appears before confirmation.
- [x] 7. Cancellation makes no changes.
- [ ] 8. Confirmation starts the appropriate rabbit hole.
- [ ] 9. Household-member transactions return only the seller from a rabbit hole.
- [x] 10. Targets move out of the active household without hard deletion.
- [x] 11. Payment is deposited exactly once and only after target processing.
- [ ] 12. Unborn transactions safely conclude the selected pregnancy.
- [ ] 13. Twins and triplets affect the live pregnancy offer.
- [ ] 14. Sellers receive trait-appropriate buffs.
- [ ] 15. Other selected pregnant Sims receive reaction buffs.
- [x] 16. Transactions validate and fail safely, including transfer rollback.
- [x] 17. Pricing and transaction logic have automated tests.
- [x] 18. The mod builds installable `.package` and `.ts4script` files.
- [x] 19. Current user-facing text uses localization resources.
- [x] 20. Build, installation, architecture, and usage documentation exists.
