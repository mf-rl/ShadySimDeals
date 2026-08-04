# Computer Household Sale Design

## Scope

Add **Sell Household Member** to compatible computers while preserving the
existing phone workflow. Add `SPECS_CHECKLIST.md` as the repository-wide status
map for every implementation phase and acceptance criterion in `SPECS.md`.

Unborn-Nooboo sales, real rabbit holes, buffs, relationship consequences,
persistent registries, and delayed outcomes remain outside this release.

## Architecture

The existing phone interaction owns behavior that both entry points need. Move
that picker, offer, confirmation, transfer, payment, and notification flow into
one shared household-sale interaction class. The phone and computer classes
inherit it and provide only entry-point metadata. Domain filtering, pricing,
validation, target processing, and payment continue through the existing shared
services.

Lot51 Core remains the only injection dependency. Add the computer affordance
through its object-tag injector so compatible custom computers are covered
without maintaining a list of tuning IDs. Keep the selected tag and injector
field in one tuning snippet and document any value that still needs confirmation
against the installed Lot51 TDESC or supported game tuning.

## Data Flow

1. The player selects **Sell Household Member** on a phone or computer.
2. The shared interaction filters active-household `SimInfo` records.
3. The native Sim picker opens, including an empty picker when no candidates
   qualify.
4. Selection calculates the offer through `SimSalePricingService`.
5. Cancellation makes no changes; confirmation invokes the same
   `TransactionOrchestrator` used by the phone.
6. The target transfers to **ShadySimDeals Holdings**, payment is deposited once,
   and the shared completion notification appears.

## Tuning and Packaging

- Package the existing computer household-member interaction tuning.
- Add or extend a Lot51 injector that targets compatible computers by object tag.
- Do not package the unborn computer interaction in this release.
- Preserve the existing custom phone category and phone injection unchanged.
- Update the DBPF resource tests to assert exact computer interaction and injector
  references.

## Failure Handling

Both entry points retain the same integration boundary: picker or dialog errors
are logged, stale selections fail validation, transfer failures do not pay, and a
payment failure triggers the existing transfer rollback. Computer injection must
not use direct monkey-patching or override EA computer tuning.

## Testing

- Prove phone and computer classes share the same household-sale implementation.
- Run the picker flow through the computer class with fake native dialogs.
- Assert the package contains the computer interaction and its injector reference.
- Assert the unborn computer resource remains absent.
- Run the complete Python test suite and build both distributable files.

## Documentation Checklist

Create `SPECS_CHECKLIST.md` with sections matching the six implementation phases
and the twenty acceptance criteria in `SPECS.md`. Mark an item complete only when
the repository implementation, automated tests, or confirmed in-game testing
supports it. Use partial sub-items where a broad phase is only partly complete,
and leave unverifiable game behavior unchecked.
