# Sale Traits and Moodlets Design

## Goal

Replace the process-local sold-Sim marker with save-managed Sim traits and add
visible, darkly satirical consequences to successful household-member and
unborn-Nooboo sales. Exiting to the main menu without saving must restore the
pre-sale trait state when the save is reloaded.

## Root Cause

`SoldSimRegistry` stores Sim IDs in a Python set owned by the runtime singleton.
Returning to the main menu does not restart Python, so the set survives while
the save rolls back. A trait is part of `SimInfo` and therefore follows the
game's normal save/reload semantics.

## Tuned Content

Add three permanent, visible, non-CAS-selectable gameplay traits. They do not
consume a personality-trait slot.

1. **Family Asset Liquidator**
   - Applied to every successful seller.
   - Description: "Some Sims build family trees. This Sim trims them for
     quarterly growth and calls it logistics."
2. **Outsourced by My Own Family**
   - Applied only to a household member who was sold.
   - This trait becomes the authoritative sold marker used by picker filtering.
   - Description: "This Sim learned the family plan had an unsubscribe button,
     and somebody else clicked it."
3. **Stork Claim Mysteriously Denied**
   - Applied to a non-selling pregnant Sim after their unborn Nooboo is sold.
   - Description: "The nursery plans vanished into a filing cabinet marked
     'Definitely Not Our Department.'"

Add three moodlets:

1. **Quarterly Profits, Fewer Mouths**
   - `+4 Happy` for 12 Sim hours.
   - Description: "The household budget is healthier, the headcount is lower,
     and ethics remain an optional expansion pack."
2. **Apparently, Love Had a Return Policy**
   - `+6 Sad` for 24 Sim hours.
   - Description: "Nothing says unconditional love like being reassigned to an
     undisclosed buyer."
3. **The Nursery Has Been Downsized**
   - `+10 Sad` for 48 Sim hours.
   - Description: "The crib is empty, the paperwork is sealed, and nobody can
     explain where tomorrow went."

Use private tuning instance IDs `0xEAA21FFB1081E014` through
`0xEAA21FFB1081E019` for the three traits followed by the three buffs. Add
dedicated English localization keys beginning at `0xA1100018` for their names
and descriptions.

## Successful-Sale Rules

Apply the household target's sold-marker trait immediately after transfer so
the existing rollback path can remove it if payment fails. Apply every other
trait and moodlet only after the rabbit holes complete and the transaction
successfully applies its target change and payment.

| Sale | Seller | Other Sim |
|---|---|---|
| Household member | Family Asset Liquidator + Quarterly Profits, Fewer Mouths | Outsourced by My Own Family + Apparently, Love Had a Return Policy |
| Unborn, pregnant Sim differs from seller | Family Asset Liquidator + Quarterly Profits, Fewer Mouths | Stork Claim Mysteriously Denied + The Nursery Has Been Downsized |
| Unborn, seller is pregnant Sim | Family Asset Liquidator + Quarterly Profits, Fewer Mouths | None |

Adding an already-owned permanent trait is idempotent. Repeating a successful
sale refreshes the corresponding moodlet duration using normal game buff
behavior.

Cancelled, failed, or rolled-back transactions apply no traits or moodlets.
Post-completion trait or moodlet application errors are logged after the core
sale succeeds; they must not reverse a completed household transfer, pregnancy
conclusion, or payment. Failure to add the household sold-marker trait remains
a transaction failure and uses the existing transfer rollback.

## Runtime Design

Keep the existing sold-registry interface used by processors and picker
filtering, but back its `mark_sold`, `is_sold`, and `unmark_sold` operations with
the **Outsourced by My Own Family** trait on `SimInfo`. Remove the process-local
sold-ID set from live runtime behavior. Transaction reservations remain
session-local.

Add one Sims 4 consequence adapter that resolves the three traits and buffs by
their private tuning IDs and applies the mapping above. Invoke it from the
successful completion path, where both actor and target IDs are still
available. Do not duplicate trait or buff calls across phone and computer
interactions.

## Verification

Automated tests must prove:

- sold-state checks read the sold trait rather than a Python set;
- marking and rollback add and remove the sold trait;
- each of the three successful-sale mappings applies exactly the expected trait
  and moodlet;
- cancellation and failure apply none;
- all six tuning resources and all localization strings are packaged;
- existing transaction, rabbit-hole, transfer, pregnancy, and payment tests
  remain green.

Live verification must cover household and unborn sales, visible traits and
moodlets, save-and-reload persistence, and exit-without-saving rollback.
