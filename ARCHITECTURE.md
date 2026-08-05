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
- `sims4_runtime.py`: shared phone/computer pickers, confirmation, notification, and transaction composition boundary.

## Transaction order

`CREATED -> VALIDATED -> OFFER_CALCULATED -> PLAYER_CONFIRMED -> RABBIT_HOLE_STARTED -> TARGET_DISPOSITION_PENDING -> TARGET_PROCESSED -> PAYMENT_COMPLETED -> CONSEQUENCES_APPLIED -> COMPLETED`

Cancellation is allowed before confirmation. Failures are terminal and release reservations. Repeated completion is idempotent. For household sales, the orchestrator pauses in `RABBIT_HOLE_STARTED` until the game service invokes its expiration callback; natural completion continues to transfer and payment, while cancellation fails without either. Household sales pay after the reversible transfer and roll it back if payment fails. Unborn sales use an immediate collaborator and prepay because clearing a pregnancy is irreversible; if pregnancy processing fails before completion, the orchestrator refunds that exact payment.

## Rabbit-hole integration

`Sims4RabbitHoleAdapter` maps the target age to one of three private `TwoSimRabbitHole` tunings and starts the seller and target, in that order, through EA's shared rabbit-hole service. The paired private affordances provide fixed 75-, 90-, or 120-minute durations. Only the seller's expiration callback resumes the transaction, so the target is moved to holdings before the game can return it to the active household. Startup failure or cancellation releases both transaction reservations without processing the target.

## Pricing pipeline

The service supports age, pregnancy count, traits, skills, fame, occults, and buyer demand. Household sales currently supply verified age data; unborn sales supply the pregnancy tracker's public expected offspring count. Results are rounded to the nearest 50 Simoleons and clamped.

## Pregnancy integration

Phone and computer interactions share one unborn workflow. `Sims4PregnancyAdapter` contains the patch-sensitive `is_pregnant`, `offspring_count`, and `clear_pregnancy()` calls; the runtime and pure transaction services do not reach into pregnancy trackers directly.

## Device integration

The four interaction tunings reuse minimal native phone or computer content verified against patch `1.125.59.1030`. The shared runtime base delegates to `SuperInteraction` before calling the household or unborn `_open_picker()` hook. Phone device failure is cosmetic and falls back to the picker; computer routing or device failure ends without opening one.

## Persistence

The current registries are session-local. Sold Sims themselves remain in the hidden **ShadySimDeals Holdings** household, preserving their `SimInfo`; transaction markers and reservations reset when the game process restarts. Add save-slot-aware persistence only after its hook is verified.
