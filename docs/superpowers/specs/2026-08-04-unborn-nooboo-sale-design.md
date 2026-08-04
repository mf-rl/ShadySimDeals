# Unborn Nooboo Sale Design

## Scope

Add **Sell Unborn Nooboo** to the existing ShadySimDeals phone category and
compatible computers. The playable flow is immediate: select a pregnant
household member, review an offer, confirm, safely clear the pregnancy, deposit
payment once, and show a completion notification.

Rabbit holes, device animations, buffs, relationship reactions, and forced
early determination of twins or triplets remain outside this release.

## Architecture

Phone and computer classes inherit one `_UnbornSaleInteraction` implementation.
It owns native picker and dialog coordination but delegates filtering, pricing,
validation, pregnancy operations, payment, reservations, and transaction states
to existing services.

`Sims4PregnancyAdapter` is the only pregnancy-runtime boundary. Against game
patch `1.125.59.1030`, it uses the public `PregnancyTracker.is_pregnant`,
`offspring_count`, and `clear_pregnancy()` APIs. It never removes pregnancy
moodlets directly and never calls `create_offspring_data()` while displaying an
offer.

## Candidate and Offer Flow

1. Read every active-household `SimInfo`.
2. Include a Sim only when its pregnancy tracker reports a current pregnancy and
   neither the Sim nor actor is reserved by another transaction.
3. Include the active Sim when pregnant.
4. Read `offspring_count` without generating offspring data; clamp missing or
   invalid values to one.
5. Calculate the offer through `SimSalePricingService.calculate_unborn_offer`.
6. Cancellation closes the dialog without changing pregnancy, funds, or
   reservations.

The public tracker normally reports one until the game or another mod has
generated or overridden offspring data. Therefore multiplicity pricing applies
when that public information exists, while full early-pregnancy twin/triplet
detection remains unchecked in `SPECS_CHECKLIST.md`.

## Transaction Safety

Pregnancy clearing is irreversible, so the unborn workflow prepays before target
processing. The shared orchestrator supports this only for processors declaring
that requirement:

1. Revalidate household membership, pregnancy, funds, and reservations.
2. Reserve actor and pregnant Sim. A self-target pregnancy reserves one Sim once.
3. Deposit payment and mark it completed.
4. Call `PregnancyTracker.clear_pregnancy()` and verify `is_pregnant` is false.
5. If clearing fails, remove the exact deposited amount through
   `FamilyFunds.try_remove(..., require_full_amount=True)`, reset payment state,
   and fail the transaction.
6. Release reservations in all cases.

Household-member sales keep their existing target-first, payment-second order.
If refunding fails, preserve both failure messages in the log and show the
existing failure notification; never silently swallow the compensation failure.

## Validation

The transaction validator distinguishes household-member and unborn targets.
Household-member rules remain unchanged. Unborn transactions allow actor and
target to be the same Sim, require a current pregnancy through the adapter, and
still require active-household membership, available household funds, a live
zone, and unreserved participants.

`TransactionRegistry` treats duplicate participant IDs as one reservation so a
pregnant actor can sell their own unborn Nooboo without falsely colliding with
themselves.

## Tuning and Localization

- Package `phone_sell_unborn_nooboo.xml` and
  `computer_sell_unborn_nooboo.xml`.
- Assign both to the existing ShadySimDeals category.
- Add the phone interaction to the Sim phone affordance injection.
- Add the computer interaction to the `Func_Computer` affordance injection.
- Add localized picker title/body strings while reusing the existing unborn
  completion and failure strings.

## Testing

- Pregnant actor and other pregnant household members are eligible.
- Non-pregnant, invalid, sold, and reserved Sims are excluded.
- Reading offspring count does not generate pregnancy data.
- Phone and computer share one unborn interaction implementation.
- Cancellation performs no mutation.
- Prepayment occurs before pregnancy clearing and exactly once.
- Clearing failure refunds the exact payment and releases reservations.
- Self-target reservations do not collide.
- Package tests assert both unborn resources and injector references.
- Full tests and distributable builds pass before installation.
