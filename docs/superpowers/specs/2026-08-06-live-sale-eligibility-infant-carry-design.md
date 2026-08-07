# Live Sale Eligibility and Infant Carry Design

## Scope

Fix three live-mode defects without changing pricing, sale durations, payment ordering, or transaction recovery:

- relationship penalties must include the sold Sim's close relatives and remaining household members;
- both sale pickers must exclude Sims who are not currently instantiated on the active lot;
- selling an infant must make the seller pick up the infant before both enter the existing shared rabbit hole.

## Root causes

The wider relationship audience is discovered only after the target has been transferred to the hidden holding household. That makes the consequence calculation depend on household and genealogy state after disposition instead of the state that was confirmed by the player.

The shared picker eligibility functions validate household membership and transaction state but never check `SimInfo.is_instanced()`. Sims at work, school, or otherwise off-lot therefore remain selectable.

The shared rabbit-hole service pushes the same routing interaction to both participants. An infant cannot satisfy that route independently, so the infant interaction ends with a transition failure and cancels the transaction. EA's standard infant pickup affordance also rejects an infant already carried by another Sim; that state requires the native handoff continuation instead.

## Design

### Relationship audience snapshot

Before target disposition, `Sims4SaleConsequences` captures the wider relationship deltas on the transaction. The snapshot excludes the seller and target, assigns `-25` to other remaining household members, assigns `-50` to the target's immediate family and spouse, and keeps the stronger value when groups overlap.

After transfer and payment succeed, the existing consequence pass consumes that snapshot. Lookup and per-Sim relationship failures remain isolated and logged; they never reverse an otherwise completed sale.

### On-lot picker filtering

Both `eligible_household_member_ids` and `eligible_unborn_ids` require `sim_info.is_instanced()` in addition to their existing rules. The normal default excludes hidden instances, matching the requirement that candidates be physically available on the active lot. A failed presence check excludes that candidate.

### Infant pickup before rabbit-hole entry

For household-member sales whose target age is `infant`, `Sims4RabbitHoleAdapter` resolves the seller and infant instances. An uncarried infant uses EA's native `socialSuperInteraction_CarryPickUp_Infant` affordance (`271032`) with a script interaction context.

When another Sim is carrying the infant, the adapter follows EA's handoff pattern: the current carrier queues continuation `269721`, targets the seller, and supplies the infant as `carry_target`. The adapter starts the existing age-based shared rabbit hole only after the interaction finishes naturally and the infant's parent/carrier is the seller. If pickup, handoff, or final ownership verification fails, the adapter completes the transaction callback as canceled. Non-infant household sales and unborn sales keep their current path unchanged.

## Error handling

- Audience capture failures are logged by source and leave the successful sale recoverable.
- Off-lot or uninspectable candidates are omitted rather than exposed as transactions that will fail later.
- Pickup or handoff startup, completion, or ownership-verification failure cancels before transfer or payment.
- Existing rabbit-hole startup and expiration callback cleanup remains authoritative after pickup.

## Verification

Automated regression tests will prove:

- wider relationship IDs are captured before target processing and consumed afterward;
- both picker helpers exclude non-instanced Sims;
- uncarried infants queue native pickup before the shared rabbit hole;
- infants carried by another Sim use native handoff before the shared rabbit hole;
- pickup, handoff, or ownership-verification failure cancels without starting the rabbit hole;
- non-infant and unborn paths remain unchanged.

Live verification will cover the reported three-Sim relationship scenario, work/school filtering in both pickers, successful uncarried pickup, successful handoff from another carrier, cancellation, and unchanged payment/transfer ordering.
