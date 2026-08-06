# Wider Relationship Consequences Design

## Goal

After a successful household-member sale, apply friendship losses to the sold
Sim's close relatives and the seller's remaining household members. Sentiments,
new buffs, and persistent grudges remain separate future work.

## Behavior

- The sold target keeps the existing `-100` friendship change toward the seller.
- Each close relative of the sold target loses `50` friendship with the seller.
- Each other member of the seller's current household loses `25` friendship
  with the seller.
- A Sim who qualifies as both a close relative and a household witness receives
  only the stronger `-50` change.
- The seller and sold target are excluded from the wider audience.
- Unborn-Nooboo sales keep their existing direct-participant behavior and do not
  apply these wider consequences.
- Cancelled, failed, and rolled-back sales apply no wider consequences.

Close relatives are the target's parents, children, siblings, and spouse. The
implementation resolves only those direct relationships and the current
household; it does not scan every Sim in the save.

## Architecture

Extend `Sims4SaleConsequences`, the existing shared post-success game boundary.
Keep the current direct-target relationship logic unchanged, then perform one
deduplicated wider-audience pass for household-member transactions.

The adapter receives injectable collaborators for current-household membership
and close-relative lookup. Live defaults isolate the supported-patch Sims 4
household and genealogy calls inside `sims4_adapters.py`; host tests provide
small fakes. No new transaction state, service abstraction, dependency, tuning
resource, or phone/computer-specific path is added.

## Data Flow

1. The orchestrator completes target processing and payment.
2. `Sims4SaleConsequences` applies the existing traits, moodlets, and direct
   seller/target relationship effect.
3. For a household-member sale, it obtains the seller's current household
   members and the target's direct close relatives.
4. It removes the seller and target, merges duplicate Sim IDs, and assigns
   `-50` to relatives or `-25` to household-only witnesses.
5. It applies each friendship change from the affected Sim toward the seller.

## Failure Handling

Wider consequences are best-effort effects after the irreversible core sale.
Each affected Sim is processed independently. A missing SimInfo, unavailable
relationship tracker, invalid genealogy result, or score-update failure logs
`wider_relationship_consequence_failed` with the transaction and affected Sim
IDs, then processing continues with the remaining audience. No consequence
failure reverses a transfer, pregnancy conclusion, or payment.

Failure while discovering one audience source does not suppress the other:
household witnesses can still be processed if genealogy lookup fails, and close
relatives can still be processed if household lookup fails.

## Testing

Automated tests cover:

- household-only witnesses receiving `-25`;
- parents, children, siblings, and spouses receiving `-50`;
- relatives who are also witnesses receiving one `-50` change;
- seller and target exclusion;
- no wider effects for unborn sales;
- deterministic processing without a save-wide Sim scan;
- one affected Sim failing without blocking the remaining Sims or raising;
- cancellation and failure retaining the orchestrator's existing success-only
  consequence ordering.

The full test suite and package build run after implementation.

## Documentation

Update `README.md`, `ARCHITECTURE.md`, `DEVELOPMENT.md`, and
`SPECS_CHECKLIST.md` to describe the implemented friendship-only wider effects.
Keep sentiments, consequence buffs for observers, and persistent grudges
explicitly deferred. Live verification remains unchecked until confirmed on
patch `1.125.59.1030`.
