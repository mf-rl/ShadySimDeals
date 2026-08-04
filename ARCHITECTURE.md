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

Cancellation is allowed before confirmation. Failures are terminal and release reservations. Repeated completion is idempotent. Household sales pay after the reversible transfer and roll it back if payment fails. Unborn sales prepay because clearing a pregnancy is irreversible; if pregnancy processing fails before completion, the orchestrator refunds that exact payment.

## Pricing pipeline

The service supports age, pregnancy count, traits, skills, fame, occults, and buyer demand. Household sales currently supply verified age data; unborn sales supply the pregnancy tracker's public expected offspring count. Results are rounded to the nearest 50 Simoleons and clamped.

## Pregnancy integration

Phone and computer interactions share one unborn workflow. `Sims4PregnancyAdapter` contains the patch-sensitive `is_pregnant`, `offspring_count`, and `clear_pregnancy()` calls; the runtime and pure transaction services do not reach into pregnancy trackers directly.

## Device integration

The four interaction tunings reuse minimal native phone or computer content verified against patch `1.125.59.1030`. The shared runtime base delegates to `SuperInteraction` before calling the household or unborn `_open_picker()` hook. Phone device failure is cosmetic and falls back to the picker; computer routing or device failure ends without opening one.

## Persistence

The current registries are session-local. Sold Sims themselves remain in the hidden **ShadySimDeals Holdings** household, preserving their `SimInfo`; transaction markers and reservations reset when the game process restarts. Add save-slot-aware persistence only after its hook is verified.
