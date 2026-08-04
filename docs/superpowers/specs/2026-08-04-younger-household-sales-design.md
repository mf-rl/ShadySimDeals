# Younger Household Sales Design

## Goal

Allow Sell Household Member to select and sell newborn/baby, infant, toddler, and child Sims, while preserving the existing Teen-through-Elder behavior on both phone and computer.

## Design

Extend the shared Sims 4 age normalization and household-sale age whitelist with `BABY`, `INFANT`, `TODDLER`, and `CHILD`. All entry points already route through the same eligibility, picker, pricing, validation, and transaction services, so no device-specific or age-specific transaction path is needed.

The existing SimInfo picker remains the source of candidates. This supports household members that do not have an instantiated Sim, including newborns. Existing configured prices and rabbit-hole durations for the four younger ages remain unchanged.

Successful transactions continue to move the selected SimInfo into the hidden holding household. The mod will not hard-delete a newborn, bassinet, or any genealogy data. If the game leaves an empty bassinet after transfer, it may remain as a normal lot object.

## Failure Handling

The existing transaction validation, rollback, payment ordering, and notifications apply unchanged. Unsupported or unrecognized game ages remain ineligible and cannot reach the transaction service.

## Verification

- Unit-test Sims 4 enum normalization for every supported household-sale age.
- Unit-test eligibility and picker behavior for newborn/baby through elder, including actor exclusion.
- Run the full automated test suite and build the package and script artifacts.
- Live-test younger-age selection and sale, with special attention to newborn transfer and bassinet behavior.
- Update `SPECS_CHECKLIST.md` only after the corresponding automated and live checks pass.
