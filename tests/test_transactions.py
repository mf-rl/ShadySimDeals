import pytest

from shady_sim_deals.models import SaleOffer, SaleTransaction
from shady_sim_deals.orchestrator import TransactionOrchestrator


class Recorder:
    def __init__(self, events, failure=None):
        self.events = events
        self.failure = failure

    def validate(self, transaction, check_reservations=True):
        self.events.append("validate")
        return self.failure

    def reserve(self, transaction):
        self.events.append("reserve")

    def release(self, transaction):
        self.events.append("release")

    def run(self, transaction, on_finished):
        self.events.append("rabbit_hole")

    def process(self, transaction):
        self.events.append("target")
        if self.failure:
            raise RuntimeError(self.failure)

    def rollback(self, transaction):
        self.events.append("rollback")

    def deposit(self, household_id, amount):
        self.events.append(("payment", household_id, amount))

    def withdraw(self, household_id, amount):
        self.events.append(("refund", household_id, amount))

    def apply(self, transaction):
        self.events.append("consequences")


def build(events, validator_failure=None, target_failure=None):
    return TransactionOrchestrator(
        Recorder(events, validator_failure),
        Recorder(events),
        Recorder(events),
        Recorder(events, target_failure),
        Recorder(events),
        Recorder(events),
    )


def transaction():
    return SaleTransaction("household_member", "actor", "target", "home")


class DelayedRabbitHole:
    def __init__(self, events):
        self.events = events
        self.callback = None

    def run(self, transaction, on_finished):
        self.events.append("rabbit_hole")
        self.callback = on_finished
        return True


def test_household_completion_waits_for_rabbit_hole_expiration():
    events = []
    rabbit_hole = DelayedRabbitHole(events)
    workflow = TransactionOrchestrator(
        Recorder(events),
        Recorder(events),
        rabbit_hole,
        Recorder(events),
        Recorder(events),
        Recorder(events),
    )
    deal = transaction()
    workflow.prepare(deal, SaleOffer(5000, {}, "buyer"))

    assert workflow.confirm_and_complete(deal)
    assert deal.state == "rabbit_hole_started"
    assert "target" not in events
    assert ("payment", "home", 5000) not in events

    rabbit_hole.callback(canceled=False)

    assert deal.state == "completed"
    assert events.index("target") < events.index(("payment", "home", 5000))
    assert events[-1] == "release"


def test_consequence_audience_is_captured_before_target_processing():
    events = []

    class CapturingConsequences(Recorder):
        def capture(self, transaction):
            self.events.append("capture_consequences")

    workflow = TransactionOrchestrator(
        Recorder(events),
        Recorder(events),
        Recorder(events),
        Recorder(events),
        Recorder(events),
        CapturingConsequences(events),
    )
    deal = transaction()
    workflow.prepare(deal, SaleOffer(5000, {}, "buyer"))

    assert workflow.confirm_and_complete(deal)
    assert events.index("capture_consequences") < events.index("target")
    assert events.index("target") < events.index("consequences")


def test_cancelled_rabbit_hole_does_not_process_or_pay():
    events = []
    rabbit_hole = DelayedRabbitHole(events)
    workflow = TransactionOrchestrator(
        Recorder(events),
        Recorder(events),
        rabbit_hole,
        Recorder(events),
        Recorder(events),
        Recorder(events),
    )
    deal = transaction()
    workflow.prepare(deal, SaleOffer(5000, {}, "buyer"))
    workflow.confirm_and_complete(deal)

    rabbit_hole.callback(canceled=True)

    assert deal.state == "failed"
    assert deal.failure_reason == "Rabbit hole was canceled"
    assert "target" not in events
    assert not any(
        isinstance(event, tuple) and event[0] == "payment" for event in events
    )
    assert events[-1] == "release"


def test_target_is_revalidated_after_rabbit_hole_wait():
    events = []
    validator = Recorder(events)
    rabbit_hole = DelayedRabbitHole(events)
    workflow = TransactionOrchestrator(
        validator,
        Recorder(events),
        rabbit_hole,
        Recorder(events),
        Recorder(events),
        Recorder(events),
    )
    deal = transaction()
    workflow.prepare(deal, SaleOffer(5000, {}, "buyer"))
    workflow.confirm_and_complete(deal)
    validator.failure = "Target left the active household"

    rabbit_hole.callback(canceled=False)

    assert deal.state == "failed"
    assert deal.failure_reason == "Target left the active household"
    assert "target" not in events
    assert not any(
        isinstance(event, tuple) and event[0] == "payment" for event in events
    )


def test_immediate_completion_observer_failure_does_not_reopen_transaction():
    events = []
    workflow = build(events)
    deal = transaction()
    workflow.prepare(deal, SaleOffer(5000, {}, "buyer"))

    def fail_observer(transaction):
        raise RuntimeError("notification failed")

    with pytest.raises(RuntimeError, match="notification failed"):
        workflow.confirm_and_complete(deal, fail_observer)

    assert deal.state == "completed"
    assert deal.failure_reason is None
    assert events.count("release") == 1


def test_payment_occurs_after_target_and_only_once():
    events = []
    workflow = build(events)
    deal = transaction()
    assert workflow.prepare(deal, SaleOffer(5000, {}, "buyer"))
    assert workflow.confirm_and_complete(deal)
    assert workflow.confirm_and_complete(deal)
    assert events.index("target") < events.index(("payment", "home", 5000))
    assert events.count(("payment", "home", 5000)) == 1
    assert deal.state == "completed"


def test_failed_validation_does_not_reserve_process_or_pay():
    events = []
    deal = transaction()
    assert not build(events, validator_failure="target left household").prepare(deal, SaleOffer(5000, {}, "buyer"))
    assert deal.state == "failed"
    assert not any(isinstance(event, tuple) and event[0] == "payment" for event in events)


def test_cancelled_transaction_does_not_process_or_pay():
    events = []
    workflow = build(events)
    deal = transaction()
    workflow.prepare(deal, SaleOffer(5000, {}, "buyer"))
    workflow.cancel(deal)
    assert deal.state == "cancelled"
    assert "target" not in events


def test_failed_target_processing_prevents_payment():
    events = []
    workflow = build(events, target_failure="pregnancy completion failed")
    deal = SaleTransaction("unborn", "actor", "pregnant", "home")
    workflow.prepare(deal, SaleOffer(15000, {}, "buyer"))
    assert not workflow.confirm_and_complete(deal)
    assert deal.state == "failed"
    assert not any(isinstance(event, tuple) and event[0] == "payment" for event in events)


def test_payment_failure_rolls_back_processed_target():
    events = []
    funds = Recorder(events)

    def fail_deposit(household_id, amount):
        events.append(("payment", household_id, amount))
        raise RuntimeError("deposit failed")

    funds.deposit = fail_deposit
    target = Recorder(events)
    workflow = TransactionOrchestrator(
        Recorder(events),
        Recorder(events),
        Recorder(events),
        target,
        funds,
        Recorder(events),
    )
    deal = transaction()
    workflow.prepare(deal, SaleOffer(5000, {}, "buyer"))

    assert not workflow.confirm_and_complete(deal)
    assert events.index("target") < events.index(("payment", "home", 5000))
    assert events[-2:] == ["rollback", "release"]
    assert not deal.payment_completed
    assert deal.state == "failed"


def test_irreversible_target_is_prepaid_before_processing():
    events = []
    target = Recorder(events)
    target.requires_prepayment = True
    workflow = TransactionOrchestrator(
        Recorder(events),
        Recorder(events),
        Recorder(events),
        target,
        Recorder(events),
        Recorder(events),
    )
    deal = SaleTransaction("unborn", "actor", "pregnant", "home")
    workflow.prepare(deal, SaleOffer(15000, {}, "buyer"))

    assert workflow.confirm_and_complete(deal)
    assert events.index(("payment", "home", 15000)) < events.index("target")
    assert deal.payment_completed


def test_failed_irreversible_target_refunds_prepayment():
    events = []
    target = Recorder(events, failure="pregnancy completion failed")
    target.requires_prepayment = True
    workflow = TransactionOrchestrator(
        Recorder(events),
        Recorder(events),
        Recorder(events),
        target,
        Recorder(events),
        Recorder(events),
    )
    deal = SaleTransaction("unborn", "actor", "pregnant", "home")
    workflow.prepare(deal, SaleOffer(15000, {}, "buyer"))

    assert not workflow.confirm_and_complete(deal)
    assert events[-2:] == [("refund", "home", 15000), "release"]
    assert not deal.payment_completed
