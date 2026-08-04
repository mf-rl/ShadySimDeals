"""Target processing policies kept separate from transaction orchestration."""


class HouseholdMemberTargetProcessor:
    def __init__(self, household_adapter, outcome_service, sold_registry):
        self._households = household_adapter
        self._outcomes = outcome_service
        self._sold = sold_registry

    def process(self, transaction):
        self._households.transfer_to_holding_household(transaction.target_id)
        self._sold.mark_sold(transaction.target_id)
        transaction.outcome = self._outcomes.apply(transaction)

    def rollback(self, transaction):
        self._households.rollback_transfer(transaction.target_id)
        self._sold.unmark_sold(transaction.target_id)
        transaction.outcome = None


class UnbornTargetProcessor:
    requires_prepayment = True

    def __init__(self, pregnancy_adapter):
        self._pregnancies = pregnancy_adapter

    def process(self, transaction):
        if not self._pregnancies.is_pregnant(transaction.target_id):
            raise ValueError("Selected Sim is no longer pregnant")
        if not self._pregnancies.conclude_pregnancy(transaction.target_id):
            raise RuntimeError("The pregnancy could not be safely concluded")
        transaction.outcome = "pregnancy_concluded"
