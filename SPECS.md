```text
You are implementing a The Sims 4 script mod named ShadySimDeals.

Read all Markdown documentation, source files, build scripts, configuration files, and existing project conventions in the repository before making changes.

The mod must allow the active Sim to sell members of the active household or sell an unborn child through interactions available on both phones and computers.

The tone must match The Sims universe: absurd, satirical, exaggerated, and very darkly comedic. Avoid graphic visuals or explicit depictions. The transaction itself must occur through a rabbit hole.

Implement this as a maintainable, extensible mod using appropriate separation of concerns, object-oriented design, SOLID principles, reusable services, dependency inversion where useful, and automated tests for logic that can be tested outside the game runtime.

Do not duplicate business logic between phone and computer interactions. Both entry points must use the same underlying transaction workflow and domain services.

==================================================
1. INITIAL REPOSITORY ANALYSIS
==================================================

Before implementing:

1. Inspect the complete repository.
2. Identify:
   - Existing Python package structure.
   - Existing XML tuning files.
   - Existing build and packaging workflow.
   - Existing injection framework, if any.
   - Existing logging utilities.
   - Existing configuration system.
   - Existing localization or string-table conventions.
   - Existing tests.
3. Determine the supported Sims 4 game version and Python version.
4. Determine whether the project uses:
   - Sims 4 Community Library.
   - XML Injector.
   - A custom interaction injection mechanism.
   - Direct monkey-patching.
5. Reuse existing abstractions and conventions where appropriate.
6. Document any game APIs or tuning identifiers that cannot be confidently determined.

Do not invent tuning IDs or game API signatures without verification. When a required game identifier is unknown, isolate it behind a clearly named constant or adapter and add a TODO explaining what must be verified in Sims 4 Studio or game tuning files.

==================================================
2. FEATURE OVERVIEW
==================================================

The mod must expose a ShadySimDeals application through:

1. The active Sim’s phone.
2. Computers available on the current lot.

Both entry points must provide these actions:

- Liquidate a Family Asset
- Monetize Future Family Growth

The phone and computer interactions must invoke the same application service and transaction workflow.

For the first implementation, use native Sims 4 interaction dialogs and Sim pickers. Do not create a completely custom Scaleform or UI screen unless the repository already includes a stable custom UI framework.

The computer version is considered feasible when implemented as:

- A ShadySimDeals pie-menu category or interaction.
- Native choice dialogs.
- Native Sim picker dialogs.
- Custom localized labels, descriptions, and icons where supported.

==================================================
3. PHONE INTERACTIONS
==================================================

Add a phone category or app named:

ShadySimDeals

It must expose:

1. Liquidate a Family Asset
2. Monetize Future Family Growth

When either action is selected:

1. Trigger an appropriate phone-call animation or phone-use animation.
2. Open the appropriate filtered Sim picker.
3. Calculate an offer for the selected Sim or pregnancy.
4. Show a confirmation dialog.
5. On confirmation, start the corresponding rabbit-hole workflow.
6. On cancellation, make no changes.

Suggested confirmation dialog:

Title:
A Definitely Legitimate Offer

Body:
A buyer has offered §{price} for {target_name}. Processing fees, suspicious paperwork, and absolutely no refunds are included.

Buttons:
- Complete Deal
- Suddenly Develop Morals

Use localized string resources rather than hard-coded user-facing text.

==================================================
4. COMPUTER INTERACTIONS
==================================================

Inject a ShadySimDeals interaction into compatible computers.

It must expose the same two actions:

1. Liquidate a Family Asset
2. Monetize Future Family Growth

The computer workflow must behave exactly like the phone workflow after the initial interaction is selected.

The interaction should use computer-related animations while browsing or contacting the buyer, followed by the same picker, confirmation, rabbit-hole, transaction, payment, and consequence services used by the phone.

Suggested computer labels:

- Browse ShadySimDeals
- Access the Definitely Legal Marketplace
- Review Untraceable Offers

Do not duplicate filtering, pricing, transaction, or consequence logic in the computer interaction implementation.

==================================================
5. SELL HOUSEHOLD MEMBER PICKER
==================================================

When Liquidate a Family Asset is selected, open a Sim picker containing:

- All on-lot members of the active household.
- Exclude the active Sim.
- Include Sims of every age:
  - Baby
  - Infant
  - Toddler
  - Child
  - Teen
  - Young Adult
  - Adult
  - Elder
- Include supported occult Sims.
- Exclude invalid, destroyed, hidden, or otherwise unsafe SimInfo records.
- Exclude Sims at work, school, or otherwise off-lot.
- Exclude pets unless explicitly supported by a future configuration option.
- Exclude Sims already marked as sold.
- Exclude Sims currently participating in another ShadySimDeals transaction.

The picker operates on `SimInfo` and requires a visible instantiated Sim on the active lot. This keeps babies and other valid on-lot ages available while excluding work, school, and other off-lot states that cannot safely enter the transaction.

After selection, refer to the selected Sim internally as the target Sim.

==================================================
6. SELL UNBORN NOOBOO PICKER
==================================================

When Monetize Future Family Growth is selected, open a Sim picker containing only pregnant Sims from the active household.

Requirements:

- Include the active Sim when the active Sim is pregnant.
- Include other pregnant household members.
- Exclude pregnant Sims at work, school, or otherwise off-lot.
- Exclude Sims whose pregnancies are invalid, completed, or already involved in a transaction.
- Determine the expected offspring count through the game pregnancy tracker if safely available.
- Do not rely only on visible pregnancy buffs.
- Do not remove pregnancy by merely deleting pregnancy moodlets.

The pregnancy transaction must safely conclude or clear the pregnancy through the appropriate game pregnancy APIs.

Isolate pregnancy-related game calls inside a dedicated adapter or service so they can be changed if game internals differ between versions.

==================================================
7. RABBIT-HOLE WORKFLOW: HOUSEHOLD MEMBER
==================================================

After the player confirms the sale:

1. Reserve the actor and target Sim for the transaction.
2. Add a visible queued interaction.
3. For non-infants, route both Sims off the active lot and place both in a shared rabbit-hole state.
4. For infants, make the seller pick up or receive the infant, route while carrying it, and register only the seller in the 90-minute rabbit hole.
5. Complete the transaction after the configured duration.
6. Return only the active Sim.
7. Remove the target Sim from the active household.
8. Deposit the payment into the active household funds.
9. Apply seller buffs and relationship consequences.
10. Resolve the target outcome.
11. Clear all transaction reservations and temporary state.
12. Show a completion notification.

Recommended default duration:

- Baby, infant, toddler, or child: 90 minutes.
- Teen, young adult, or adult: 120 minutes.
- Elder: 75 minutes.
- Celebrity or high-risk target: add 30 minutes.
- Actor with high Mischief or Criminal-career experience: optionally reduce duration.
- Clamp the final duration between 60 and 240 Sim minutes.

Use a configuration service so durations can be changed without modifying transaction code.

Recommended queued-interaction name:

Attend a Definitely Legal Exchange

Alternative localized names may include:

- Handle Some Family Business
- Finalize an Untraceable Transaction
- Discuss Alternative Household Placement
- Exchange Plumbobs in an Alley
- Sign Papers Without Reading Them
- Visit the No-Questions Department

==================================================
8. RABBIT-HOLE WORKFLOW: UNBORN NOOBOO
==================================================

When the selected pregnant Sim is the active Sim:

1. The active Sim enters the rabbit hole alone.
2. The transaction runs for the configured duration.
3. The pregnancy is safely concluded.
4. The active Sim returns.
5. The payment is deposited.
6. Appropriate buffs and consequences are applied.

When the selected pregnant Sim is another household member:

1. The active Sim and pregnant Sim both enter the rabbit hole.
2. The transaction runs for the configured duration.
3. The pregnancy is safely concluded.
4. Both Sims return.
5. The payment is deposited.
6. The seller receives a seller buff.
7. The pregnant Sim receives a reaction buff.
8. Their relationship may change according to the outcome.

Recommended default duration:

- 90 Sim minutes.
- Add 30 minutes for twins.
- Add 60 minutes for triplets.
- Clamp to a maximum of 180 Sim minutes.

Recommended queued-interaction name:

Arrange a Pre-Order

Alternative names:

- Attend a Prenatal Business Meeting
- Discuss the Nooboo’s Financial Future
- Negotiate an Early Release
- Liquidate Future Dependents
- Make Room for Profit

==================================================
9. TARGET SIM OUTCOME
==================================================

Do not hard-delete sold Sims by default.

Hard deletion can damage or invalidate:

- Genealogy.
- Relationships.
- Sentiments.
- Clubs.
- Careers.
- Story progression references.
- References maintained by other mods.

Implement a target disposition abstraction with at least these outcomes:

1. Hidden disappearance.
2. Later escape or return.
3. Mysterious ghost return.
4. Transaction reversal.

For the initial version, hidden disappearance must be the default.

Recommended implementation:

1. Remove the target from the active household.
2. Transfer the target to a special unplayed household, such as:
   ShadySimDeals Holdings
3. Apply a hidden trait or marker:
   ShadySimDeals_Sold
4. Prevent normal spawning, walkbys, phone calls, venue visits, and story-progression use where safely possible.
5. Preserve SimInfo, genealogy, relationships, and other references.
6. Remove or fade the target from the current zone after the rabbit-hole transaction.

Create a dedicated SoldSimRepository or SoldSimRegistry abstraction responsible for tracking sold Sims.

Do not scatter hidden-trait checks throughout unrelated classes.

==================================================
10. RANDOM TARGET OUTCOMES
==================================================

Implement configurable weighted outcomes.

Default suggested probabilities:

- Hidden permanently: 80%
- Escapes and returns later: 12%
- Returns as a ghost: 5%
- Transaction reversed by buyer: 3%

For babies, infants, toddlers, and children:

- Disable the ghost outcome by default.
- Redistribute its probability to hidden disappearance or transaction reversal.

All probabilities must be configurable.

Use a seeded or injectable random-number abstraction so outcome selection can be unit tested.

For the initial MVP, it is acceptable to implement only:

- Hidden disappearance.
- Ghost return.

However, structure the code so additional outcomes can be added without changing the core transaction orchestration.

==================================================
11. GHOST RETURN
==================================================

When the ghost outcome is selected for an eligible target:

1. Preserve the target SimInfo.
2. Apply an appropriate death type through a safe game API.
3. Preserve genealogy.
4. Delay the return by a configurable number of Sim days.
5. Return or spawn the Sim as a ghost.
6. Apply a permanent or long-duration vendetta marker.
7. Set a strongly negative relationship toward the seller.
8. Apply a sentiment if supported.
9. Do not automatically add the ghost to the active household.

Suggested notification:

Title:
An Unsatisfied Customer Has Returned

Body:
Apparently, “no refunds” does not cover the afterlife.

Possible ghost behaviors for future extension:

- Haunt the seller’s home.
- Break household objects.
- Frighten the seller.
- Interrupt future transactions.
- Send threatening messages.
- Reduce future offers.

For the first version, implement only the safe and reliable subset supported by the current project architecture.

==================================================
12. PRICE CALCULATION
==================================================

Create a dedicated pricing domain service.

Example interface:

class SimSalePricingService:
    def calculate_household_member_offer(self, target_sim_info, buyer_context) -> SaleOffer:
        ...

    def calculate_unborn_offer(self, pregnant_sim_info, buyer_context) -> SaleOffer:
        ...

The calculation must be deterministic when the same buyer context and random seed are supplied.

Use the following conceptual formula:

Final Price =
    Base Age Value
    × Trait Multiplier
    × Skill Multiplier
    × Status Multiplier
    × Market Demand Multiplier
    × Risk Multiplier
    + Special Bonuses

Round the result to the nearest §50.

Apply configurable minimum and maximum prices.

Recommended defaults:

- Minimum offer: §1,000
- Maximum ordinary offer: §50,000
- Maximum rare-special offer: §100,000

==================================================
13. BASE PRICE BY AGE
==================================================

Use these configurable default values:

- Unborn child: §15,000
- Baby: §13,500
- Infant: §12,000
- Toddler: §10,000
- Child: §8,000
- Teen: §6,500
- Young Adult: §5,000
- Adult: §4,000
- Elder: §2,500

The younger the target, the higher the base value.

Do not hard-code these values directly inside the pricing algorithm. Store them in configuration or a dedicated pricing table.

==================================================
14. MULTIPLE-PREGNANCY PRICING
==================================================

Apply these default total multipliers:

- One unborn child: 100%
- Twins: 180%
- Triplets: 240%

Example with a §15,000 unborn base price:

- One child: §15,000
- Twins: §27,000
- Triplets: §36,000

If the game supports more than three expected offspring through mods, calculate the value using an extensible strategy rather than throwing an error.

==================================================
15. TRAIT PRICE MODIFIERS
==================================================

Trait values represent buyer demand, not an objective value assigned to a person.

Use configurable modifiers.

Suggested positive modifiers:

- Genius: +20%
- Creative: +15%
- Active: +10%
- Self-Assured: +12%
- Ambitious: +15%
- Cheerful: +8%
- Good: +5%
- Rare reward traits: +5% to +25%
- Occult-specific traits: +20% to +60%

Suggested negative or buyer-dependent modifiers:

- Lazy: -10%
- Slob: -12%
- Gloomy: -8%
- Hot-Headed: -10%
- Erratic: -15%
- Noncommittal: -8%
- Evil: buyer-dependent
- Kleptomaniac: buyer-dependent

Do not bind pricing directly to localized trait names.

Use trait tuning IDs or stable trait references stored in a mapping adapter.

Unknown or unsupported traits must contribute no modifier rather than causing an error.

==================================================
16. SKILL PRICE MODIFIERS
==================================================

For teens and older:

Skill bonus:

- Highest skill level × 2%
- Second-highest skill level × 1%
- Third-highest skill level × 0.5%

Cap total skill bonus at +35%.

For children and toddlers:

- Use a reduced cap of +10%.
- Use only skills safely accessible for their age.

Ignore unavailable, hidden, or invalid skills.

Put skill extraction behind a SimAttributesAdapter so pricing logic can be tested without loading the game runtime.

==================================================
17. CAREER, EDUCATION, FAME, AND OCCULT MODIFIERS
==================================================

Suggested configurable values:

Career:

- Career levels 1–3: +2% per level
- Career levels 4–7: +3% per level
- Career levels 8–10: +4% per level

Education:

- High-school graduate: +5%
- University degree: +15%
- Distinguished degree: +25%

Fame:

- Minor celebrity: +10%
- Rising star: +20%
- Proper celebrity: +35%
- Global superstar: +75%

Occults:

- Alien: +30%
- Vampire: +35%
- Spellcaster: +30%
- Werewolf: +25%
- Mermaid: +25%
- Ghost: +40%

All pack-dependent checks must fail gracefully when the corresponding pack is not installed.

Do not import pack-specific modules unconditionally if doing so can prevent the mod from loading.

==================================================
18. MARKET DEMAND
==================================================

Implement a buyer-demand multiplier.

Default range:

0.80 to 1.40

For the MVP, buyer demand may be randomly generated.

Preferred design:

BuyerProfile:
- buyer_id
- display_name
- trait_preferences
- occult_preferences
- skill_preferences
- risk_tolerance
- demand_multiplier
- descriptive_text

Potential future buyer profiles:

- Wealthy Household
- Criminal Syndicate
- Mad Scientist
- Occult Collector
- Questionable Adoption Agency
- Mysterious Stranger

The pricing service must accept a BuyerProfile or BuyerContext even if the initial UI does not display multiple buyer choices.

==================================================
19. PAYMENT
==================================================

Payment must be deposited only after the transaction successfully completes.

Requirements:

- Never pay before the rabbit hole completes.
- Never pay twice.
- Use an idempotent transaction-completion guard.
- Add funds to the active household.
- Log the transaction.
- Show the final amount in a notification.
- Roll back or avoid partial state where possible if payment or household transfer fails.

Suggested completion notification:

Title:
Another Successful Reassignment

Body:
The household received §{price}. {target_name} is now somebody else’s paperwork problem.

For an unborn transaction:

Title:
Premium Pre-Order Completed

Body:
The household received §{price}. The nursery has become unexpectedly spacious.

==================================================
20. SELLER BUFF SYSTEM
==================================================

Create a seller-reaction service.

Buff selection must consider:

- Seller traits.
- Transaction type.
- Target age.
- Offer value.
- Relationship between seller and target.
- Whether the target later returns.
- Whether the transaction was unusually profitable.
- Whether the seller has family-oriented or moral traits.

Use a priority-based rule system rather than a large monolithic conditional block.

Suggested trait reactions:

- Evil: Confident or Happy.
- Materialistic: Happy.
- Ambitious: Confident.
- Kleptomaniac: Energized.
- Family-Oriented: Very Sad.
- Good: Guilty or Very Sad.
- Loyal: Very Tense.
- Noncommittal: Fine or Happy.
- Erratic: Random appropriate emotion.
- Gloomy: Sad with increased duration.
- Self-Assured: Confident.
- Snob: Embarrassed when the offer was low.
- Hot-Headed: Angry when the buyer paid below expected value.

Implement at least five seller buffs in the MVP.

==================================================
21. SUGGESTED SELLER BUFFS
==================================================

Questionably Good Business
Emotion: Confident
Duration: 8 hours
Description:
There are profits, there are families, and there are profits from families.

The Household Is Finally Profitable
Emotion: Happy
Duration: 12 hours
Description:
Some Sims contribute by working. Others contribute by suddenly disappearing.

Nooboo Futures Are Up
Emotion: Confident
Duration: 8 hours
Only for unborn transactions.
Description:
The prenatal market remains disturbingly bullish.

One Less Mouth, Several More Simoleons
Emotion: Happy
Duration: 10 hours
Description:
Budgeting has never felt this morally flexible.

A Sudden Attack of Conscience
Emotion: Sad
Duration: 24 hours
Description:
The money is real. Unfortunately, so is the memory.

Someone Is Asking Questions
Emotion: Tense
Duration: 16 hours
Description:
Apparently, Sims notice when their relatives disappear.

That Was Probably Fine
Emotion: Uncomfortable
Duration: 8 hours
Description:
Everything is fine. The briefcase is fine. The unmarked vehicle was fine.

An Empty Bassinet, a Full Wallet
Emotion: Sad or Uncomfortable
Duration: 24 hours
Only for unborn transactions.
Description:
The nursery feels considerably larger now.

Sold Below Market Value
Emotion: Embarrassed
Duration: 12 hours
Description:
Betraying one’s family is bad enough. Doing it at a discount is humiliating.

Worth Every Relative
Emotion: Very Confident
Duration: 12 hours
Description:
Some sacrifices are difficult. This one came with five figures.

All names and descriptions must use localization resources.

==================================================
22. PREGNANT SIM REACTION
==================================================

When the pregnant Sim is not the actor, assign a reaction based on:

- Relationship with the actor.
- Relevant traits.
- Randomized complicity outcome.
- Whether the offer was high or low.

Suggested internal outcomes:

- Complicit.
- Regretful.
- Betrayed.

Suggested default probabilities:

Relationship at least 50:
- Complicit: 40%
- Regretful: 35%
- Betrayed: 25%

Relationship from 0 to 49:
- Complicit: 20%
- Regretful: 40%
- Betrayed: 40%

Relationship below 0:
- Complicit: 10%
- Regretful: 25%
- Betrayed: 65%

Suggested effects:

Complicit:
- Small positive relationship change.
- Confident or Happy buff.

Regretful:
- Negative relationship change.
- Sad or Tense buff.

Betrayed:
- Large negative relationship change.
- Angry, Sad, or Very Tense buff.
- Optional long-term hidden grudge marker.

Make the random selector injectable and unit testable.

==================================================
23. RELATIONSHIP CONSEQUENCES
==================================================

Before removing the sold target from the active household:

1. Capture relevant relationships.
2. Identify close relatives and household members.
3. Apply reactions after transaction completion.

Possible effects:

- Close relatives receive a Where Did They Go? buff.
- Witnesses lose friendship with the seller.
- Family-Oriented household members become suspicious.
- Complicit Sims may gain relationship with the seller.
- Returning targets receive a severe negative relationship toward the seller.
- Returning ghosts receive a permanent grudge or vendetta marker.
- The seller and returned target should become enemies or near-enemies.

Do not iterate through every Sim in the save unnecessarily.

Limit relationship processing to:

- Current household members.
- Close family members.
- Sims with meaningful relationship values.
- Sims directly involved in the transaction.

==================================================
24. VALIDATION AND SAFETY GUARDS
==================================================

Every transaction must validate:

- Actor exists.
- Actor belongs to the active household.
- Target exists.
- Target belongs to the same household at confirmation time.
- Actor and target are not already reserved.
- Target is not already sold.
- Target is not being deleted or destroyed.
- Required trackers are available.
- Household has valid funds storage.
- Pregnancy is still active for unborn transactions.
- Rabbit-hole participants can route or safely transition off-lot.
- The transaction has not already completed.
- The save is not currently shutting down.
- The selected target has not left the household between picker selection and confirmation.

When validation fails:

- Cancel safely.
- Clear temporary state.
- Do not remove Sims.
- Do not alter pregnancy.
- Do not pay funds.
- Show a localized failure notification.
- Write a useful log entry.

==================================================
25. TRANSACTION STATE MACHINE
==================================================

Model the workflow as an explicit state machine.

Suggested states:

- CREATED
- VALIDATED
- OFFER_CALCULATED
- PLAYER_CONFIRMED
- RABBIT_HOLE_STARTED
- TARGET_DISPOSITION_PENDING
- TARGET_PROCESSED
- PAYMENT_COMPLETED
- CONSEQUENCES_APPLIED
- COMPLETED
- CANCELLED
- FAILED

Invalid state transitions must be rejected and logged.

Transaction completion must be idempotent.

Use a unique transaction identifier.

Persist transaction state only if required by delayed outcomes or save/load support.

==================================================
26. PROPOSED ARCHITECTURE
==================================================

Use names appropriate to the existing repository, but aim for a structure similar to:

shady_sim_deals/
    __init__.py
    bootstrap/
        mod_bootstrap.py
        interaction_registration.py
    interactions/
        phone/
            open_shady_sim_deals.py
            sell_household_member.py
            sell_unborn_nooboo.py
        computer/
            open_shady_sim_deals.py
            sell_household_member.py
            sell_unborn_nooboo.py
        rabbit_holes/
            household_member_transaction.py
            unborn_transaction.py
    application/
        transaction_orchestrator.py
        transaction_factory.py
        offer_application_service.py
    domain/
        models/
            sale_offer.py
            sale_transaction.py
            buyer_profile.py
            transaction_outcome.py
        pricing/
            pricing_service.py
            age_pricing_strategy.py
            trait_pricing_strategy.py
            skill_pricing_strategy.py
            status_pricing_strategy.py
        outcomes/
            target_outcome_strategy.py
            hidden_disappearance_strategy.py
            ghost_return_strategy.py
        reactions/
            seller_reaction_service.py
            pregnant_sim_reaction_service.py
        state/
            transaction_state_machine.py
    infrastructure/
        sims/
            household_adapter.py
            pregnancy_adapter.py
            relationship_adapter.py
            sim_attributes_adapter.py
            rabbit_hole_adapter.py
            funds_adapter.py
            sim_picker_adapter.py
        persistence/
            sold_sim_registry.py
            transaction_registry.py
        configuration/
            mod_config.py
            pricing_config.py
            probability_config.py
        localization/
            string_ids.py
        logging/
            logger.py
    tuning/
        interactions/
        buffs/
        traits/
        snippets/
        strings/
    tests/
        unit/
        integration/

Adapt this structure to the repository rather than forcing unnecessary folders.

==================================================
27. CONFIGURATION
==================================================

Create centralized configuration for:

- Base prices by age.
- Price caps.
- Trait modifiers.
- Career modifiers.
- Education modifiers.
- Fame modifiers.
- Occult modifiers.
- Skill cap.
- Market-demand range.
- Rabbit-hole duration by transaction type.
- Outcome probabilities.
- Ghost-return eligibility.
- Ghost-return delay.
- Whether computer interactions are enabled.
- Whether phone interactions are enabled.
- Whether child ghost outcomes are allowed.
- Logging verbosity.

Prefer immutable configuration objects or read-only mappings.

Do not spread numeric constants across interaction classes.

==================================================
28. LOGGING
==================================================

Implement structured logging.

Log:

- Mod initialization.
- Interaction injection success or failure.
- Picker opening.
- Target selection.
- Offer calculation breakdown.
- Confirmation or cancellation.
- Rabbit-hole start and completion.
- Household transfer.
- Pregnancy conclusion.
- Payment.
- Outcome selection.
- Buff assignment.
- Relationship consequences.
- Validation failures.
- Exceptions.

Do not log personally identifying user information beyond Sim names and internal IDs needed for debugging.

Prefix logs consistently with:

[ShadySimDeals]

Unexpected errors must be caught at Sims-runtime boundaries so the mod does not break unrelated game interactions.

==================================================
29. LOCALIZATION
==================================================

All visible text must use string-table resources.

Include English localization for:

- Phone app name.
- Computer category.
- Interaction names.
- Picker titles.
- Confirmation dialogs.
- Failure dialogs.
- Completion notifications.
- Buff names.
- Buff descriptions.
- Rabbit-hole names.
- Ghost-return notification.
- Relationship-related notifications.

Do not hard-code English strings directly in Python or tuning XML unless required temporarily for debugging.

Use a stable naming convention for string keys.

==================================================
30. TESTING
==================================================

Write automated tests for all pure or isolated logic.

Minimum required tests:

Pricing:
- Younger Sims have a higher base value than older Sims.
- Unborn child pricing works.
- Twin and triplet multipliers work.
- Trait modifiers are applied.
- Unknown traits are ignored.
- Skill bonuses are capped.
- Fame modifiers are applied.
- Occult modifiers are applied.
- Price minimum and maximum caps work.
- Prices round to the nearest §50.
- Buyer-demand multipliers work deterministically.

Filtering:
- Actor is excluded from household-member picker.
- Pregnant actor is included in unborn picker.
- Non-pregnant Sims are excluded from unborn picker.
- Sold Sims are excluded.
- Invalid SimInfo records are excluded.

Transactions:
- Payment occurs only after target processing.
- Payment cannot occur twice.
- Failed validation does not alter funds.
- Cancelled transaction does not remove Sims.
- Invalid state transitions are rejected.
- Completion is idempotent.

Outcomes:
- Weighted outcome selection respects configured probabilities.
- Child ghost outcome is disabled by default.
- Random behavior is deterministic with a supplied seed.

Buffs:
- Good and Family-Oriented sellers receive negative reactions.
- Evil or Materialistic sellers can receive positive reactions.
- Low-price transactions can trigger Sold Below Market Value.
- High-price transactions can trigger Worth Every Relative.

Pregnancy:
- Pregnancy adapter is invoked only after confirmation.
- Failed pregnancy completion prevents payment.
- Multiple-offspring pricing uses the expected offspring count.

Mock or fake Sims runtime dependencies.

Do not require the actual game runtime for unit tests.

==================================================
31. BUILD AND PACKAGING
==================================================

Update the existing build workflow so the result produces the appropriate Sims 4 mod artifacts.

Expected output may include:

- ShadySimDeals.package
- ShadySimDeals.ts4script

Use the repository’s existing conventions.

Ensure:

- Python files are packaged correctly into the .ts4script archive.
- Tuning and string resources are included in the .package.
- Source-only files and tests are excluded from release artifacts.
- Package names are stable and versioned according to project conventions.
- Build instructions are documented.

Do not introduce a new build system if the repository already has one that can be extended.

==================================================
32. DOCUMENTATION
==================================================

Update or create documentation covering:

README:
- Mod overview.
- Features.
- Installation.
- Phone usage.
- Computer usage.
- Pricing summary.
- Rabbit-hole behavior.
- Target disappearance behavior.
- Ghost-return possibility.
- Configuration.
- Compatibility.
- Known limitations.
- Troubleshooting.
- Uninstallation warning.

ARCHITECTURE:
- Main modules.
- Transaction state machine.
- Pricing pipeline.
- Sims runtime adapters.
- Interaction injection.
- Outcome strategies.
- Persistence approach.

DEVELOPMENT:
- Required tools.
- Sims 4 Studio workflow.
- Python version.
- Build commands.
- Test commands.
- How to find or update tuning IDs.
- How to add a new buyer profile.
- How to add a new seller buff.
- How to add a new target outcome.

Add a clear warning that uninstalling the mod while Sims are stored in the hidden holding household may make recovery difficult.

==================================================
33. IMPLEMENTATION PHASES
==================================================

Implement in this order:

Phase 1:
- Repository analysis.
- Project skeleton.
- Logging.
- Configuration.
- Shared transaction models.
- Pricing service.
- Unit tests.

Phase 2:
- Phone interaction injection.
- Computer interaction injection.
- Native action selection.
- Filtered Sim pickers.
- Confirmation dialogs.

Phase 3:
- Household-member rabbit hole.
- Household transfer.
- Payment.
- Seller buffs.
- Relationship consequences.

Phase 4:
- Pregnancy picker.
- Pregnancy adapter.
- Unborn rabbit hole.
- Multiple-offspring pricing.
- Pregnant Sim reaction.

Phase 5:
- Hidden sold-Sim household.
- Sold-Sim registry.
- Ghost-return outcome.
- Delayed events.

Phase 6:
- Packaging.
- Localization.
- Documentation.
- Compatibility checks.
- Final regression tests.

Do not begin custom UI development as part of the MVP.

==================================================
34. ACCEPTANCE CRITERIA
==================================================

The feature is complete when:

1. ShadySimDeals appears on supported phones.
2. ShadySimDeals appears on supported computers.
3. Both expose:
   - Liquidate a Family Asset.
   - Monetize Future Family Growth.
4. The household-member picker:
   - Includes all valid household members.
   - Excludes the actor.
5. The unborn picker:
   - Includes only pregnant household members.
   - Includes the actor when pregnant.
6. The player sees a calculated offer before confirming.
7. Cancelling makes no changes.
8. Confirming starts the appropriate rabbit hole.
9. A household-member transaction returns only the seller.
10. The target is removed from the active household without unsafe hard deletion.
11. Payment is deposited exactly once.
12. An unborn transaction safely concludes the selected pregnancy.
13. Twins and triplets affect pricing.
14. The seller receives a trait-appropriate buff.
15. Another selected pregnant Sim receives a reaction buff.
16. Transactions are validated and fail safely.
17. Pricing and transaction logic have automated tests.
18. The mod builds into installable .package and .ts4script files.
19. User-facing text is localized.
20. Build, installation, architecture, and usage documentation are included.

==================================================
35. CODE QUALITY REQUIREMENTS
==================================================

- Use descriptive names.
- Keep interaction classes thin.
- Place business logic in services or domain strategies.
- Avoid global mutable state.
- Avoid hard-coded tuning IDs throughout the codebase.
- Use dependency injection or explicit dependency construction.
- Keep Sims runtime adapters separate from pure logic.
- Prefer composition over inheritance unless Sims APIs require inheritance.
- Catch exceptions at integration boundaries.
- Add type hints where compatible with the Sims Python runtime.
- Add docstrings to public abstractions and non-obvious game integration code.
- Do not add unnecessary abstractions with only one trivial caller.
- Do not silently swallow exceptions.
- Do not leave the repository in a partially broken state.
- Preserve backward compatibility with existing functionality.

==================================================
36. FINAL RESPONSE
==================================================

After implementation, provide:

1. A concise summary of the implementation.
2. A list of added and modified files.
3. The architecture and main design decisions.
4. Any tuning IDs or game APIs that still require verification.
5. Build instructions.
6. Test instructions.
7. Installation instructions.
8. Known limitations.
9. Recommended next steps.
10. Confirmation of whether both phone and computer interactions were successfully implemented.

If a game API or tuning requirement prevents a complete implementation, do not fake it.

Instead:

- Implement the surrounding architecture.
- Add a safe placeholder or adapter.
- Clearly identify the unresolved integration point.
- Explain exactly what must be inspected in Sims 4 Studio or the game tuning files.
```
