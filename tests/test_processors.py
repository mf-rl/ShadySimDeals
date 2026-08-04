from shady_sim_deals.models import SaleTransaction
from shady_sim_deals.processors import HouseholdMemberTargetProcessor, UnbornTargetProcessor
from shady_sim_deals.registry import SoldSimRegistry, TransactionRegistry


class FakeHouseholds:
    def __init__(self):
        self.transferred = []
        self.rolled_back = []

    def transfer_to_holding_household(self, sim_id):
        self.transferred.append(sim_id)

    def rollback_transfer(self, sim_id):
        self.rolled_back.append(sim_id)


class FakeOutcomes:
    def apply(self, transaction):
        return "hidden"


class FakePregnancy:
    def __init__(self, pregnant=True, result=True):
        self.pregnant = pregnant
        self.result = result
        self.calls = []

    def is_pregnant(self, sim_id):
        self.calls.append(("check", sim_id))
        return self.pregnant

    def conclude_pregnancy(self, sim_id):
        self.calls.append(("conclude", sim_id))
        return self.result


def test_household_processor_transfers_marks_and_applies_outcome():
    households = FakeHouseholds()
    sold = SoldSimRegistry()
    deal = SaleTransaction("household_member", "actor", "target", "home")
    HouseholdMemberTargetProcessor(households, FakeOutcomes(), sold).process(deal)
    assert households.transferred == ["target"]
    assert sold.is_sold("target")
    assert deal.outcome == "hidden"


def test_pregnancy_processor_checks_before_concluding():
    pregnancy = FakePregnancy()
    deal = SaleTransaction("unborn", "actor", "target", "home")
    UnbornTargetProcessor(pregnancy).process(deal)
    assert pregnancy.calls == [("check", "target"), ("conclude", "target")]


def test_unborn_processor_requires_prepayment():
    assert UnbornTargetProcessor.requires_prepayment is True


def test_registry_reserves_and_releases_both_participants():
    registry = TransactionRegistry()
    deal = SaleTransaction("household_member", "actor", "target", "home")
    registry.reserve(deal)
    assert registry.is_reserved("actor") and registry.is_reserved("target")
    registry.release(deal)
    assert not registry.is_reserved("actor") and not registry.is_reserved("target")


def test_household_processor_rollback_restores_target_and_sold_marker():
    households = FakeHouseholds()
    sold = SoldSimRegistry()
    deal = SaleTransaction("household_member", "actor", "target", "home")
    processor = HouseholdMemberTargetProcessor(households, FakeOutcomes(), sold)
    processor.process(deal)

    processor.rollback(deal)

    assert households.rolled_back == ["target"]
    assert not sold.is_sold("target")
    assert deal.outcome is None
