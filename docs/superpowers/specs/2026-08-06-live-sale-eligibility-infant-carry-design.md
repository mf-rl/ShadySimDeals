# Live Sale Eligibility and Infant Carry Design

## Scope

Fix three live-mode defects without changing pricing, sale durations, payment ordering, or transaction recovery:

- relationship penalties must include the sold Sim's close relatives and remaining household members;
- both sale pickers must exclude Sims who are not currently instantiated on the active lot;
- selling an infant must make the seller carry the infant into a 90-minute rabbit hole without giving the infant an independent routing interaction.

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

When another Sim is carrying the infant, the adapter follows EA's handoff pattern: the current carrier queues continuation `269721` and targets the seller. Before the push, the adapter assigns the infant to `InteractionContext.carry_target`, matching EA's picker continuation contract. It does not pass `carry_target` as an interaction keyword argument.

After the interaction finishes naturally and ownership verification confirms that the seller carries the infant, the adapter registers only the seller in the existing private 90-minute solo rabbit hole. The infant remains the seller's carry attachment, so both route to the exit and disappear together without pushing an independent rabbit-hole interaction to the infant. On natural expiration, the existing transaction callback transfers the infant and completes payment before the seller returns alone. If pickup, handoff, final ownership verification, rabbit-hole startup, or rabbit-hole completion fails, the transaction is canceled without transfer or payment. Non-infant household sales and unborn sales keep their current paths unchanged.

## Error handling

- Audience capture failures are logged by source and leave the successful sale recoverable.
- Off-lot or uninspectable candidates are omitted rather than exposed as transactions that will fail later.
- Pickup or handoff startup, completion, or ownership-verification failure cancels before transfer or payment.
- Existing rabbit-hole startup and expiration callback cleanup remains authoritative after pickup; cancellation leaves the infant in the source household and makes no payment.

## Verification

Automated regression tests prove:

- wider relationship IDs are captured before target processing and consumed afterward;
- both picker helpers exclude non-instanced Sims;
- uncarried infants queue native pickup before a seller-only 90-minute rabbit hole;
- infants carried by another Sim use native handoff before that seller-only rabbit hole;
- the infant is never registered as a second rabbit-hole participant;
- pickup, handoff, or ownership-verification failure cancels without starting the rabbit hole;
- non-infant and unborn paths remain unchanged.

Live verification confirmed the reported three-Sim relationship scenario, work/school filtering in both pickers, and successful handoff from another carrier into a seller-only 90-minute infant sale with transfer and payment. The remaining acceptance cases stay tracked in `SPECS_CHECKLIST.md`.
