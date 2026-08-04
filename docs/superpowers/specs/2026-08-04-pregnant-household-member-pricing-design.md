# Pregnant Household-Member Pricing Design

## Goal

Price a pregnant household member as a bundle containing both the selected Sim and the active pregnancy, while keeping the pregnancy intact after transfer.

## Pricing

Calculate the selected Sim's normal household-member value, then add the configured unborn value as a special pregnancy bonus. Use the existing offspring multipliers:

- Singleton: +15,000
- Twins: +27,000
- Triplets: +36,000
- More than three: use the existing extensible pregnancy multiplier

Apply the existing ordinary maximum of 50,000 to the combined offer and round through the current pricing service. Include pregnancy_bonus in the offer breakdown. Non-pregnant household-member pricing remains unchanged.

Pricing is deterministic. Random buyer-discovery pricing and new flavor text are outside this change.

## Runtime Behavior

Use Sims4PregnancyAdapter.is_pregnant and expected_offspring_count when building a household-sale candidate for both the preview dialog and confirmed transaction. Do not use visible pregnancy moodlets.

Selling a pregnant household member transfers the Sim through the existing native household lifecycle. It does not clear or otherwise alter the pregnancy. Sell Unborn Nooboo remains the separate option that concludes the pregnancy while retaining the Sim.

## Verification

- Unit-test non-pregnant, singleton, twin, triplet, and capped combined offers.
- Unit-test runtime candidate construction from the pregnancy adapter.
- Verify preview and completed payment use the bundled amount.
- Run the full suite and build.
- Live-test a singleton pregnant household-member sale: bundled offer, one payment, target removed, pregnancy retained.
