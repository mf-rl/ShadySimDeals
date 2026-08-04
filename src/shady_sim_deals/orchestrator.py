"""Shared application workflow used by phone and computer interactions."""

from .state_machine import TransactionStateMachine


class TransactionError(RuntimeError):
    pass


class TransactionOrchestrator:
    def __init__(
        self,
        validator,
        reservations,
        rabbit_holes,
        target_processor,
        funds,
        consequences,
        state_machine=None,
    ):
        self._validator = validator
        self._reservations = reservations
        self._rabbit_holes = rabbit_holes
        self._target_processor = target_processor
        self._funds = funds
        self._consequences = consequences
        self._states = state_machine or TransactionStateMachine()

    def prepare(self, transaction, offer):
        error = self._validator.validate(transaction)
        if error:
            transaction.failure_reason = str(error)
            self._states.transition(transaction, "failed")
            return False
        self._states.transition(transaction, "validated")
        transaction.offer = offer
        self._states.transition(transaction, "offer_calculated")
        return True

    def cancel(self, transaction):
        self._states.transition(transaction, "cancelled")
        self._reservations.release(transaction)

    def confirm_and_complete(self, transaction):
        if transaction.state == "completed":
            return True
        if transaction.state != "offer_calculated":
            raise TransactionError("Transaction is not ready for confirmation")
        target_processed = False
        try:
            error = self._validator.validate(transaction)
            if error:
                raise TransactionError(str(error))
            self._reservations.reserve(transaction)
            self._states.transition(transaction, "player_confirmed")
            self._rabbit_holes.run(transaction)
            self._states.transition(transaction, "rabbit_hole_started")
            self._states.transition(transaction, "target_disposition_pending")
            self._target_processor.process(transaction)
            target_processed = True
            self._states.transition(transaction, "target_processed")
            if not transaction.payment_completed:
                self._funds.deposit(transaction.household_id, transaction.offer.amount)
                transaction.payment_completed = True
            self._states.transition(transaction, "payment_completed")
            self._consequences.apply(transaction)
            self._states.transition(transaction, "consequences_applied")
            self._states.transition(transaction, "completed")
            return True
        except Exception as exc:
            transaction.failure_reason = str(exc)
            if target_processed and not transaction.payment_completed:
                rollback = getattr(self._target_processor, "rollback", None)
                if callable(rollback):
                    try:
                        rollback(transaction)
                    except Exception as rollback_exc:
                        transaction.failure_reason += "; rollback failed: {}".format(
                            rollback_exc
                        )
            if transaction.state not in ("completed", "failed"):
                self._states.transition(transaction, "failed")
            return False
        finally:
            self._reservations.release(transaction)
