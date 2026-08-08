# Architecture

## Modules

- `pricing.py`: deterministic offer calculation over pure candidate data.
- `filtering.py`: shared household and pregnancy picker predicates.
- `state_machine.py`: rejects invalid transaction transitions.
- `orchestrator.py`: validation, reservation, rabbit hole, target processing, payment, and consequences.
- `processors.py`: household transfer and pregnancy-specific target handling.
- `outcomes.py` and `reactions.py`: pure outcome selection and reaction rules; only pregnant-Sim relationship selection is wired into the live runtime.
- `registry.py`: participant reservations and the pure sold registry used by domain tests.
- `sims4_adapters.py`: all version-sensitive game calls, including live trait-backed sold filtering and sale consequences.
- `sims4_runtime.py`: shared phone/computer pickers, confirmation, notification, and transaction composition boundary.

## Transaction order

`CREATED -> VALIDATED -> OFFER_CALCULATED -> PLAYER_CONFIRMED -> RABBIT_HOLE_STARTED -> TARGET_DISPOSITION_PENDING -> TARGET_PROCESSED -> PAYMENT_COMPLETED -> CONSEQUENCES_APPLIED -> COMPLETED`

Cancellation is allowed before confirmation. Failures are terminal and release reservations. Repeated completion is idempotent. Every sale pauses in `RABBIT_HOLE_STARTED` until the game service invokes its expiration callback; natural completion continues to target processing and payment, while cancellation fails without either. Household sales pay after the reversible transfer and roll it back if payment fails. Unborn sales prepay immediately before the irreversible pregnancy conclusion at expiration; if pregnancy processing fails, the orchestrator refunds that exact payment.

## Rabbit-hole integration

`Sims4RabbitHoleAdapter` maps toddler-through-elder household targets by age to private 75-, 90-, or 120-minute `TwoSimRabbitHole` tunings. Newborn `SimInfo` records resolve their matching `Baby` object through the object manager. Infants use EA pickup affordance `271032`, or handoff continuation `269721` when carried by another Sim. Newborns use native Check On affordance `275655`, whose continuation enters persistent Held Actions `275181`; when another Sim is carrying the newborn, that carrier first completes the native visible put-down naturally. Once the newborn is detached, a seller-owned basic object reservation prevents another caregiver from reacquiring it until Check On finishes. After carry ownership is verified, only the seller is registered in the private 90-minute solo `RabbitHole`; the target stays attached to the seller and receives no independent routing interaction. Unborn sales map expected offspring to private 90-, 120-, or 150-minute tunings: self-target sales use `RabbitHole`, while other targets use `TwoSimRabbitHole` with the seller first. Only the seller's expiration callback resumes either transaction. Household targets then move to holdings before the seller returns; unborn participants return before payment and pregnancy conclusion. Startup failure or cancellation releases reservations without processing the target.

## Pricing pipeline

The service supports age, pregnancy count, traits, skills, fame, occults, and buyer demand. Household sales currently supply verified age and pregnancy-count data; unborn sales supply the pregnancy tracker's public expected offspring count. Results are rounded to the nearest 50 Simoleons and clamped.

## Pregnancy integration

Phone and computer interactions share one unborn workflow. `Sims4PregnancyAdapter` contains the patch-sensitive `is_pregnant`, `offspring_count`, and `clear_pregnancy()` calls; the runtime and pure transaction services do not reach into pregnancy trackers directly.

## Relationship consequences

`Sims4SaleConsequences` snapshots the household and close-relative audience after rabbit-hole revalidation but before target transfer, then applies friendship changes after target processing and payment. Household targets lose 100 friendship with the seller. Their immediate genealogy and spouse lose 50, while other Sims remaining in the seller's household lose 25; the deduplicated pass applies only the stronger loss to overlapping Sims and never scans the full save. Other pregnant targets use the injected `PregnantSimReactionService` to apply +10, -25, or -75 from their current friendship score; self-target unborn sales make no relationship change. Discovery and score-update failures are isolated per source or affected Sim and never reverse the completed sale.

## Device integration

The four interaction tunings reuse minimal native phone or computer content verified against patch `1.125.59.1030`. The shared runtime base delegates to `SuperInteraction` before calling the household or unborn `_open_picker()` hook. Phone device failure is cosmetic and falls back to the picker; computer routing or device failure ends without opening one.

## Presentation resources

The package embeds eleven 256x256 BC3/DST5 image resources (`0x00B2D882`) compiled from the normalized source PNGs. During each build, the vendored DirectXTex `texconv.exe` creates temporary one-mip DXT5 data and `build_mod.py` rearranges its blocks into Sims 4 DST5 order; no compiled image assets are retained. Tuning and generated SimData reference the results for the shared app category, phone/computer pie-menu choices, active queue actions, permanent traits, and timed moodlets. These references are presentation-only; transaction behavior remains in the existing runtime and domain modules.

## Persistence

Live sold filtering reads the permanent **Outsourced by My Own Family** trait from the target's `SimInfo`, so it follows normal save/reload semantics without a separate persistence hook. Sold Sims remain in the hidden **ShadySimDeals Holdings** household, preserving their `SimInfo`. Participant reservations and active rabbit-hole callbacks alone remain session-local. Private sale rabbit-hole interactions are deliberately non-saveable so a reload cannot resume without its transaction callback; finish or cancel an active sale before saving.
