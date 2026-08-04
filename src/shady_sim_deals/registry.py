"""Repositories for sold Sims and active transaction reservations."""


class SoldSimRegistry:
    def __init__(self):
        self._sold_ids = set()

    def mark_sold(self, sim_id):
        self._sold_ids.add(str(sim_id))

    def is_sold(self, sim_id):
        return str(sim_id) in self._sold_ids

    def unmark_sold(self, sim_id):
        self._sold_ids.discard(str(sim_id))


class TransactionRegistry:
    def __init__(self):
        self._sim_to_transaction = {}

    def reserve(self, transaction):
        participants = (transaction.actor_id, transaction.target_id)
        if any(sim_id in self._sim_to_transaction for sim_id in participants):
            raise ValueError("A transaction participant is already reserved")
        for sim_id in participants:
            self._sim_to_transaction[sim_id] = transaction.transaction_id

    def release(self, transaction):
        for sim_id in (transaction.actor_id, transaction.target_id):
            if self._sim_to_transaction.get(sim_id) == transaction.transaction_id:
                self._sim_to_transaction.pop(sim_id, None)

    def is_reserved(self, sim_id):
        return str(sim_id) in self._sim_to_transaction
