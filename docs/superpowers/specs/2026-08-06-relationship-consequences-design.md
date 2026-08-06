# Direct Relationship Consequences Design

## Goal

Apply friendship changes between the two Sims directly involved in a successful
sale while leaving relatives, witnesses, sentiments, and long-term grudges for
later work.

## Behavior

- A sold household member loses 100 friendship with the seller.
- When another pregnant Sim's unborn Nooboo is sold, the existing
  `PregnantSimReactionService` selects an outcome from the current friendship
  score: `complicit` adds 10 friendship, `regretful` subtracts 25, and
  `betrayed` subtracts 75.
- A pregnant seller targeting themself receives no relationship change.
- Cancelled, failed, and rolled-back transactions apply no relationship change.

## Architecture

Extend `Sims4SaleConsequences`, the existing shared post-success game boundary.
After its current traits and moodlets are applied, it reads the target
`SimInfo.relationship_tracker`, selects the applicable delta, and calls the
verified patch `1.125.59.1030` API
`add_relationship_score(other_sim_id, increment)`.

Inject the pregnant-reaction selector so host tests remain deterministic. The
live default uses Python's existing `random` module; no new dependency or
configuration layer is needed.

## Failure Handling

Relationship changes are best-effort consequences after the irreversible core
sale. Missing Sims, trackers, or game API failures are logged as
`relationship_consequence_failed` and do not reverse household transfer,
pregnancy conclusion, or payment. Trait and moodlet application remains
independent so failure in either consequence type does not suppress the other.

## Testing

Automated tests cover the household-member delta, all three unborn outcomes,
self-target neutrality, deterministic selector injection, success-only ordering,
and failure logging without raising. The full test suite and package build run
after implementation.

## Documentation

Mark relationship consequences implemented in `SPECS_CHECKLIST.md`, describe
the direct-participant scope in `README.md`, and retain relatives, witnesses,
sentiments, and grudges as deferred work in `DEVELOPMENT.md`.
