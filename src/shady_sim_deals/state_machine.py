"""Explicit transaction state machine."""


class InvalidTransitionError(ValueError):
    pass


class TransactionStateMachine:
    TRANSITIONS = {
        "created": frozenset(("validated", "cancelled", "failed")),
        "validated": frozenset(("offer_calculated", "failed")),
        "offer_calculated": frozenset(("player_confirmed", "cancelled", "failed")),
        "player_confirmed": frozenset(("rabbit_hole_started", "failed")),
        "rabbit_hole_started": frozenset(("target_disposition_pending", "failed")),
        "target_disposition_pending": frozenset(("target_processed", "failed")),
        "target_processed": frozenset(("payment_completed", "failed")),
        "payment_completed": frozenset(("consequences_applied", "failed")),
        "consequences_applied": frozenset(("completed", "failed")),
        "completed": frozenset(),
        "cancelled": frozenset(),
        "failed": frozenset(),
    }

    def transition(self, transaction, next_state):
        if next_state not in self.TRANSITIONS.get(transaction.state, ()):
            raise InvalidTransitionError(
                "Invalid transaction transition: {} -> {}".format(
                    transaction.state, next_state
                )
            )
        transaction.state = next_state
