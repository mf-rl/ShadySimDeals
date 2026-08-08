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

    def confirm_and_complete(self, transaction, on_finished=None):
        if transaction.state == "completed":
            return True
        if transaction.state != "offer_calculated":
            raise TransactionError("Transaction is not ready for confirmation")
        try:
            error = self._validator.validate(transaction)
            if error:
                raise TransactionError(str(error))
            self._reservations.reserve(transaction)
            self._states.transition(transaction, "player_confirmed")
            callback = lambda canceled=False: self._finish_after_rabbit_hole(
                transaction, canceled, on_finished
            )
            self._states.transition(transaction, "rabbit_hole_started")
            started = self._rabbit_holes.run(transaction, callback)
            if transaction.state != "rabbit_hole_started":
                return transaction.state == "completed"
            if started is False:
                raise TransactionError("Rabbit hole could not start")
        except Exception as exc:
            self._fail_before_target(transaction, exc, on_finished)
            return False
        if started is None:
            callback()
        return transaction.state in ("rabbit_hole_started", "completed")

    def _finish_after_rabbit_hole(self, transaction, canceled, on_finished):
        if transaction.state != "rabbit_hole_started":
            return
        if canceled:
            transaction.failure_reason = "Rabbit hole was canceled"
            self._states.transition(transaction, "failed")
            self._reservations.release(transaction)
            if on_finished is not None:
                on_finished(transaction)
            return
        target_processed = False
        prepaid = False
        try:
            error = self._validator.validate(
                transaction, check_reservations=False
            )
            if error:
                raise TransactionError(str(error))
            capture_consequences = getattr(self._consequences, "capture", None)
            if capture_consequences is not None:
                capture_consequences(transaction)
            self._states.transition(transaction, "target_disposition_pending")
            if (
                getattr(self._target_processor, "requires_prepayment", False)
                and not transaction.payment_completed
            ):
                self._funds.deposit(
                    transaction.household_id, transaction.offer.amount
                )
                transaction.payment_completed = True
                prepaid = True
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
        except Exception as exc:
            transaction.failure_reason = str(exc)
            if prepaid and not target_processed and transaction.payment_completed:
                try:
                    self._funds.withdraw(
                        transaction.household_id, transaction.offer.amount
                    )
                    transaction.payment_completed = False
                except Exception as refund_exc:
                    transaction.failure_reason += "; refund failed: {}".format(
                        refund_exc
                    )
            elif target_processed and not transaction.payment_completed:
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
        finally:
            self._reservations.release(transaction)
            if on_finished is not None:
                on_finished(transaction)

    def _fail_before_target(self, transaction, exc, on_finished):
        transaction.failure_reason = str(exc)
        if transaction.state not in ("completed", "failed"):
            self._states.transition(transaction, "failed")
        self._reservations.release(transaction)
        if on_finished is not None:
            on_finished(transaction)
