# Architecture

## Modules

- `pricing.py`: deterministic offer calculation over pure candidate data.
- `filtering.py`: shared household and pregnancy picker predicates.
- `state_machine.py`: rejects invalid transaction transitions.
- `orchestrator.py`: validation, reservation, rabbit hole, target processing, payment, and consequences.
- `processors.py`: household transfer and pregnancy-specific target handling.
- `outcomes.py` and `reactions.py`: injected random selection and priority rules.
- `registry.py`: sold-Sim tracking and participant reservations.
- `sims4_adapters.py`: all version-sensitive game calls.
- `sims4_runtime.py`: phone picker, confirmation, notification, and transaction composition boundary.

## Transaction order

`CREATED -> VALIDATED -> OFFER_CALCULATED -> PLAYER_CONFIRMED -> RABBIT_HOLE_STARTED -> TARGET_DISPOSITION_PENDING -> TARGET_PROCESSED -> PAYMENT_COMPLETED -> CONSEQUENCES_APPLIED -> COMPLETED`

Cancellation is allowed before confirmation. Failures are terminal, release reservations, and never pay before target processing. Repeated completion is idempotent. A payment failure after transfer invokes the target processor's rollback path.

## Pricing pipeline

The service supports age, pregnancy count, traits, skills, fame, occults, and buyer demand. The playable phone MVP supplies verified age data only; results are rounded to the nearest 50 Simoleons and clamped.

## Persistence

The current registries are session-local. Sold Sims themselves remain in the hidden **ShadySimDeals Holdings** household, preserving their `SimInfo`; transaction markers and reservations reset when the game process restarts. Add save-slot-aware persistence only after its hook is verified.
