"""Version-sensitive Sims 4 operations isolated behind explicit adapters."""


class IntegrationUnavailable(RuntimeError):
    pass


def age_key(sim_info):
    name = str(getattr(getattr(sim_info, "age", None), "name", sim_info.age))
    normalized = name.replace("_", "").lower()
    ages = {
        "baby": "baby",
        "infant": "infant",
        "toddler": "toddler",
        "child": "child",
        "teen": "teen",
        "youngadult": "young_adult",
        "adult": "adult",
        "elder": "elder",
    }
    if normalized not in ages:
        raise ValueError("Unsupported age: {}".format(name))
    return ages[normalized]


class Sims4TransactionValidator:
    def __init__(
        self,
        sim_info_lookup=None,
        household_lookup=None,
        reservation_check=None,
        shutdown_check=None,
        pregnancy_check=None,
    ):
        self._sim_info_lookup = sim_info_lookup or self._find_sim_info
        self._household_lookup = household_lookup or self._find_household
        self._reservation_check = reservation_check or (lambda sim_id: False)
        self._shutdown_check = shutdown_check or self._is_shutting_down
        self._pregnancy_check = pregnancy_check or (lambda sim_id: False)

    def validate(self, transaction):
        if self._shutdown_check():
            return "The game is shutting down"
        actor = self._sim_info_lookup(str(transaction.actor_id))
        if actor is None:
            return "Actor no longer exists"
        target = self._sim_info_lookup(str(transaction.target_id))
        if target is None:
            return "Target no longer exists"
        if transaction.transaction_type == "unborn":
            if not self._pregnancy_check(transaction.target_id):
                return "Selected Sim is no longer pregnant"
        else:
            if transaction.actor_id == transaction.target_id:
                return "The actor cannot be the target"
            if getattr(target, "is_pet", False):
                return "Pets are not supported"
            try:
                age_key(target)
            except ValueError as exc:
                return str(exc)
        household = self._household_lookup(str(transaction.household_id))
        if household is None or getattr(household, "funds", None) is None:
            return "Household funds are unavailable"
        if str(getattr(actor, "household_id", "")) != transaction.household_id:
            return "Actor left the active household"
        if str(getattr(target, "household_id", "")) != transaction.household_id:
            return "Target left the active household"
        if self._reservation_check(transaction.actor_id) or self._reservation_check(
            transaction.target_id
        ):
            return "A transaction participant is already reserved"
        return None

    @staticmethod
    def _find_sim_info(sim_id):
        import services

        return services.sim_info_manager().get(int(sim_id))

    @staticmethod
    def _find_household(household_id):
        import services

        return services.household_manager().get(int(household_id))

    @staticmethod
    def _is_shutting_down():
        import services

        zone = services.current_zone()
        return zone is None or bool(getattr(zone, "is_zone_shutting_down", False))


class Sims4PregnancyAdapter:
    def __init__(self, sim_info_lookup=None):
        self._sim_info_lookup = sim_info_lookup or self._find_sim_info

    def _tracker(self, sim_id):
        sim_info = self._sim_info_lookup(str(sim_id))
        if sim_info is None:
            raise ValueError("SimInfo no longer exists")
        return getattr(sim_info, "pregnancy_tracker", None)

    def is_pregnant(self, sim_id):
        tracker = self._tracker(sim_id)
        return bool(tracker is not None and getattr(tracker, "is_pregnant", False))

    def expected_offspring_count(self, sim_id):
        tracker = self._tracker(sim_id)
        return max(1, int(getattr(tracker, "offspring_count", 1) or 1))

    def conclude_pregnancy(self, sim_id):
        tracker = self._tracker(sim_id)
        if tracker is None or not tracker.is_pregnant:
            return False
        tracker.clear_pregnancy()
        return not bool(tracker.is_pregnant)

    @staticmethod
    def _find_sim_info(sim_id):
        import services

        sim_info = services.sim_info_manager().get(int(sim_id))
        if sim_info is None:
            raise ValueError("SimInfo no longer exists")
        return sim_info


class Sims4RabbitHoleAdapter:
    def run(self, transaction):
        # Verification item: confirm the affordance and participant API in game tuning.
        raise IntegrationUnavailable("Rabbit-hole API requires Sims 4 Studio verification")


class Sims4HouseholdAdapter:
    HOLDING_HOUSEHOLD_NAME = "ShadySimDeals Holdings"

    def __init__(self, household_manager=None, sim_info_lookup=None):
        self._household_manager = household_manager
        self._sim_info_lookup = sim_info_lookup or Sims4PregnancyAdapter._find_sim_info
        self._transfers = {}

    def transfer_to_holding_household(self, sim_id):
        sim_id = str(sim_id)
        sim_info = self._sim_info_lookup(sim_id)
        if sim_info is None:
            raise ValueError("SimInfo no longer exists")
        manager = self._manager()
        source = self._get_household(manager, sim_info.household_id)
        if source is None:
            raise ValueError("Source household no longer exists")
        holdings = self._holding_household(manager, source)
        try:
            source.remove_sim_info(
                sim_info,
                destroy_if_empty_household=False,
                assign_to_none=False,
            )
            holdings.add_sim_info_to_household(sim_info)
            if sim_info in source.sim_infos or sim_info not in holdings.sim_infos:
                raise RuntimeError("household membership did not change")
        except Exception as exc:
            if sim_info not in source.sim_infos:
                try:
                    if sim_info in holdings.sim_infos:
                        holdings.remove_sim_info(
                            sim_info,
                            destroy_if_empty_household=False,
                            assign_to_none=False,
                        )
                    source.add_sim_info_to_household(sim_info)
                except Exception as rollback_exc:
                    raise IntegrationUnavailable(
                        "Holding-household transfer failed: {}; rollback failed: {}".format(
                            exc, rollback_exc
                        )
                    )
            raise IntegrationUnavailable(
                "Holding-household transfer failed: {}".format(exc)
            )
        self._transfers[sim_id] = (source.id, holdings.id)

    def rollback_transfer(self, sim_id):
        sim_id = str(sim_id)
        source_id, holdings_id = self._transfers[sim_id]
        manager = self._manager()
        source = self._get_household(manager, source_id)
        holdings = self._get_household(manager, holdings_id)
        sim_info = self._sim_info_lookup(sim_id)
        if source is None or holdings is None or sim_info is None:
            raise IntegrationUnavailable("Transfer rollback state is unavailable")
        holdings.remove_sim_info(
            sim_info,
            destroy_if_empty_household=False,
            assign_to_none=False,
        )
        source.add_sim_info_to_household(sim_info)
        if sim_info not in source.sim_infos or sim_info in holdings.sim_infos:
            raise IntegrationUnavailable("Transfer rollback verification failed")
        self._transfers.pop(sim_id, None)

    def is_transfer_complete(self, sim_id):
        sim_id = str(sim_id)
        transfer = self._transfers.get(sim_id)
        if transfer is None:
            return False
        manager = self._manager()
        source = self._get_household(manager, transfer[0])
        holdings = self._get_household(manager, transfer[1])
        sim_info = self._sim_info_lookup(sim_id)
        return bool(
            sim_info is not None
            and source is not None
            and holdings is not None
            and sim_info not in source.sim_infos
            and sim_info in holdings.sim_infos
        )

    def _manager(self):
        if self._household_manager is None:
            import services

            self._household_manager = services.household_manager()
        return self._household_manager

    @staticmethod
    def _get_household(manager, household_id):
        key = int(household_id) if str(household_id).isdigit() else household_id
        return manager.get(key)

    def _holding_household(self, manager, source):
        for household in manager.values():
            if household.name == self.HOLDING_HOUSEHOLD_NAME:
                if not household.hidden:
                    household.set_to_hidden(0)
                return household
        household = manager.create_household(source.account, 0)
        household.name = self.HOLDING_HOUSEHOLD_NAME
        household.set_to_hidden(0)
        return household


class Sims4FundsAdapter:
    def deposit(self, household_id, amount):
        import services
        from protocolbuffers import Consts_pb2

        household = services.household_manager().get(int(household_id))
        if household is None or getattr(household, "funds", None) is None:
            raise ValueError("Household funds are unavailable")
        household.funds.add(
            int(amount),
            Consts_pb2.TELEMETRY_MONEY_OBJECT_MARKETPLACE_SALE,
        )

    def withdraw(self, household_id, amount):
        import services
        from protocolbuffers import Consts_pb2

        household = services.household_manager().get(int(household_id))
        if household is None or getattr(household, "funds", None) is None:
            raise ValueError("Household funds are unavailable")
        if not household.funds.try_remove(
            int(amount),
            Consts_pb2.TELEMETRY_MONEY_OBJECT_MARKETPLACE_SALE,
            None,
            True,
        ):
            raise RuntimeError("The prepaid amount could not be refunded")
