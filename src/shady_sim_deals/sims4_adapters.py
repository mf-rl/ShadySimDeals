"""Version-sensitive Sims 4 operations isolated behind explicit adapters."""

import random

from .logging import ModLogger
from .reactions import PregnantSimReactionService


_RABBIT_HOLE_CALLBACKS = {}


def mark_rabbit_hole_callback_for_reattach(sim_id):
    pending = _RABBIT_HOLE_CALLBACKS.get(sim_id)
    if pending is not None:
        _RABBIT_HOLE_CALLBACKS[sim_id] = (pending[0], None)


def reattach_rabbit_hole_callback(sim_id, rabbit_hole_id, service):
    pending = _RABBIT_HOLE_CALLBACKS.get(sim_id)
    if pending is None:
        return
    callback, previous_rabbit_hole = pending
    rabbit_hole = service._get_rabbit_hole(sim_id, rabbit_hole_id)
    if rabbit_hole is None or rabbit_hole is previous_rabbit_hole:
        return
    service.set_rabbit_hole_expiration_callback(
        sim_id, rabbit_hole_id, callback
    )
    _RABBIT_HOLE_CALLBACKS[sim_id] = (callback, rabbit_hole)


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

    def validate(self, transaction, check_reservations=True):
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
        if check_reservations and (
            self._reservation_check(transaction.actor_id)
            or self._reservation_check(transaction.target_id)
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


class Sims4SoldSimRegistry:
    SOLD_TRAIT_ID = 0xEAA21FFB1081E015

    def __init__(self, sim_info_lookup=None, trait_lookup=None):
        self._sim_info_lookup = (
            sim_info_lookup or Sims4TransactionValidator._find_sim_info
        )
        self._trait_lookup = trait_lookup or self._find_trait

    def _state(self, sim_id):
        sim_info = self._sim_info_lookup(str(sim_id))
        trait = self._trait_lookup(self.SOLD_TRAIT_ID)
        if sim_info is None or trait is None:
            raise IntegrationUnavailable("Sold trait state is unavailable")
        return sim_info, trait

    def mark_sold(self, sim_id):
        sim_info, trait = self._state(sim_id)
        if not sim_info.has_trait(trait) and sim_info.add_trait(trait) is False:
            raise IntegrationUnavailable("Sold trait could not be added")

    def is_sold(self, sim_id):
        sim_info, trait = self._state(sim_id)
        return sim_info.has_trait(trait)

    def unmark_sold(self, sim_id):
        sim_info, trait = self._state(sim_id)
        if sim_info.has_trait(trait) and sim_info.remove_trait(trait) is False:
            raise IntegrationUnavailable("Sold trait could not be removed")

    @staticmethod
    def _find_trait(instance_id):
        import services
        import sims4.resources

        return services.get_instance_manager(
            sims4.resources.Types.TRAIT
        ).get(instance_id)


class Sims4SaleConsequences:
    SELLER_TRAIT_ID = 0xEAA21FFB1081E014
    SOLD_TRAIT_ID = 0xEAA21FFB1081E015
    LOST_UNBORN_TRAIT_ID = 0xEAA21FFB1081E016
    SELLER_BUFF_ID = 0xEAA21FFB1081E017
    SOLD_BUFF_ID = 0xEAA21FFB1081E018
    LOST_UNBORN_BUFF_ID = 0xEAA21FFB1081E019
    RELATIONSHIP_DELTAS = {
        "complicit": 10,
        "regretful": -25,
        "betrayed": -75,
    }

    def __init__(
        self,
        sim_info_lookup=None,
        trait_lookup=None,
        buff_lookup=None,
        logger=None,
        pregnant_reactions=None,
        household_member_lookup=None,
        close_relative_lookup=None,
    ):
        self._sim_info_lookup = (
            sim_info_lookup or Sims4TransactionValidator._find_sim_info
        )
        self._trait_lookup = trait_lookup or self._find_trait
        self._buff_lookup = buff_lookup or self._find_buff
        self._logger = logger or ModLogger()
        self._pregnant_reactions = (
            pregnant_reactions or PregnantSimReactionService(random)
        )
        self._household_member_lookup = (
            household_member_lookup or self._find_household_member_ids
        )
        self._close_relative_lookup = (
            close_relative_lookup or self._find_close_relative_ids
        )

    def capture(self, transaction):
        if transaction.transaction_type == "household_member":
            transaction.wider_relationship_deltas = (
                self._wider_relationship_deltas(transaction)
            )

    def apply(self, transaction):
        try:
            self._apply_traits_and_moodlets(transaction)
        except Exception:
            self._logger.exception(
                "sale_consequences_failed",
                transaction_type=transaction.transaction_type,
                actor_id=str(transaction.actor_id),
                target_id=str(transaction.target_id),
            )
        try:
            self._apply_relationship(transaction)
        except Exception:
            self._logger.exception(
                "relationship_consequence_failed",
                transaction_type=transaction.transaction_type,
                actor_id=str(transaction.actor_id),
                target_id=str(transaction.target_id),
            )
        self._apply_wider_relationships(transaction)

    def _apply_traits_and_moodlets(self, transaction):
        self._apply_pair(
            transaction.actor_id,
            self.SELLER_TRAIT_ID,
            self.SELLER_BUFF_ID,
        )
        if transaction.transaction_type == "household_member":
            self._apply_pair(
                transaction.target_id,
                self.SOLD_TRAIT_ID,
                self.SOLD_BUFF_ID,
            )
        elif transaction.actor_id != transaction.target_id:
            self._apply_pair(
                transaction.target_id,
                self.LOST_UNBORN_TRAIT_ID,
                self.LOST_UNBORN_BUFF_ID,
            )

    def _apply_relationship(self, transaction):
        if transaction.actor_id == transaction.target_id:
            return
        target = self._sim_info_lookup(str(transaction.target_id))
        tracker = getattr(target, "relationship_tracker", None)
        if tracker is None:
            raise IntegrationUnavailable("Relationship tracker is unavailable")
        actor_id = int(transaction.actor_id)
        if transaction.transaction_type == "household_member":
            delta = -100
        elif transaction.transaction_type == "unborn":
            outcome = self._pregnant_reactions.select(
                tracker.get_relationship_score(actor_id)
            )
            delta = self.RELATIONSHIP_DELTAS[outcome]
        else:
            return
        tracker.add_relationship_score(actor_id, delta)

    def _apply_wider_relationships(self, transaction):
        if transaction.transaction_type != "household_member":
            return
        deltas = getattr(transaction, "wider_relationship_deltas", None)
        if deltas is None:
            deltas = self._wider_relationship_deltas(transaction)
        actor_id = str(transaction.actor_id)
        for sim_id, delta in deltas.items():
            try:
                sim_info = self._sim_info_lookup(sim_id)
                tracker = getattr(sim_info, "relationship_tracker", None)
                if tracker is None:
                    raise IntegrationUnavailable(
                        "Relationship tracker is unavailable"
                    )
                tracker.add_relationship_score(int(actor_id), delta)
            except Exception:
                self._log_wider_failure(
                    transaction, sim_id, "relationship"
                )

    def _wider_relationship_deltas(self, transaction):
        actor_id = str(transaction.actor_id)
        target_id = str(transaction.target_id)
        deltas = {}
        try:
            for sim_id in self._household_member_lookup(actor_id):
                sim_id = str(sim_id)
                if sim_id not in (actor_id, target_id):
                    deltas[sim_id] = -25
        except Exception:
            self._log_wider_failure(transaction, None, "household")
        try:
            for sim_id in self._close_relative_lookup(target_id):
                sim_id = str(sim_id)
                if sim_id not in (actor_id, target_id):
                    deltas[sim_id] = -50
        except Exception:
            self._log_wider_failure(transaction, None, "genealogy")
        return deltas

    def _log_wider_failure(self, transaction, affected_sim_id, source):
        self._logger.exception(
            "wider_relationship_consequence_failed",
            transaction_type=transaction.transaction_type,
            actor_id=str(transaction.actor_id),
            target_id=str(transaction.target_id),
            affected_sim_id=(
                None if affected_sim_id is None else str(affected_sim_id)
            ),
            source=source,
        )

    @staticmethod
    def _find_household_member_ids(actor_id):
        actor = Sims4TransactionValidator._find_sim_info(str(actor_id))
        household = getattr(actor, "household", None)
        if household is None:
            raise IntegrationUnavailable("Actor household is unavailable")
        return tuple(str(sim_info.sim_id) for sim_info in household.sim_infos)

    @staticmethod
    def _find_close_relative_ids(target_id):
        target = Sims4TransactionValidator._find_sim_info(str(target_id))
        genealogy = getattr(target, "genealogy", None)
        if genealogy is None:
            raise IntegrationUnavailable("Target genealogy is unavailable")
        relative_ids = {
            str(sim_id)
            for sim_id in genealogy.get_immediate_family_sim_ids_gen()
        }
        spouse_id = int(getattr(target, "spouse_sim_id", 0) or 0)
        if spouse_id:
            relative_ids.add(str(spouse_id))
        return tuple(sorted(relative_ids))

    def _apply_pair(self, sim_id, trait_id, buff_id):
        sim_info = self._sim_info_lookup(str(sim_id))
        trait = self._trait_lookup(trait_id)
        buff = self._buff_lookup(buff_id)
        if sim_info is None or trait is None or buff is None:
            raise IntegrationUnavailable("Sale consequence tuning is unavailable")
        if (
            not sim_info.has_trait(trait)
            and sim_info.add_trait(trait) is False
        ):
            raise IntegrationUnavailable("Sale consequence trait could not be added")
        from objects import ALL_HIDDEN_REASONS

        sim = sim_info.get_sim_instance(
            allow_hidden_flags=ALL_HIDDEN_REASONS
        )
        if sim is None:
            raise IntegrationUnavailable("Sale consequence Sim is unavailable")
        sim.add_buff(buff)

    _find_trait = staticmethod(Sims4SoldSimRegistry._find_trait)

    @staticmethod
    def _find_buff(instance_id):
        import services
        import sims4.resources

        return services.get_instance_manager(
            sims4.resources.Types.BUFF
        ).get(instance_id)


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
    NEWBORN_HOLD_AFFORDANCE_ID = 13011
    INFANT_PICKUP_AFFORDANCE_ID = 271032
    INFANT_HANDOFF_AFFORDANCE_ID = 269721
    INFANT_SOLO_RABBIT_HOLE_ID = 0xEAA21FFB1081E00B
    RABBIT_HOLE_BY_AGE = {
        "elder": 0xEAA21FFB1081E005,
        "baby": 0xEAA21FFB1081E006,
        "infant": 0xEAA21FFB1081E006,
        "toddler": 0xEAA21FFB1081E006,
        "child": 0xEAA21FFB1081E006,
        "teen": 0xEAA21FFB1081E007,
        "young_adult": 0xEAA21FFB1081E007,
        "adult": 0xEAA21FFB1081E007,
    }
    UNBORN_SOLO_BY_COUNT = {
        1: 0xEAA21FFB1081E00B,
        2: 0xEAA21FFB1081E00D,
        3: 0xEAA21FFB1081E00F,
    }
    UNBORN_SHARED_BY_COUNT = {
        1: 0xEAA21FFB1081E00C,
        2: 0xEAA21FFB1081E00E,
        3: 0xEAA21FFB1081E010,
    }

    def __init__(
        self,
        rabbit_hole_service=None,
        sim_info_lookup=None,
        rabbit_hole_lookup=None,
        expected_offspring_lookup=None,
        infant_pickup=None,
        logger=None,
    ):
        self._service = rabbit_hole_service
        self._sim_info_lookup = (
            sim_info_lookup or Sims4PregnancyAdapter._find_sim_info
        )
        self._rabbit_hole_lookup = rabbit_hole_lookup or self._find_rabbit_hole
        self._expected_offspring_lookup = (
            expected_offspring_lookup or (lambda sim_id: 1)
        )
        self._infant_pickup = infant_pickup or self._queue_infant_pickup
        self._logger = logger or ModLogger()

    def run(self, transaction, on_finished):
        actor = self._sim_info_lookup(str(transaction.actor_id))
        target = self._sim_info_lookup(str(transaction.target_id))
        if actor is None or target is None:
            raise IntegrationUnavailable(
                "Rabbit-hole participant no longer exists"
            )
        solo = False
        if transaction.transaction_type == "unborn":
            count = min(
                3,
                max(1, int(self._expected_offspring_lookup(transaction.target_id))),
            )
            solo = transaction.actor_id == transaction.target_id
            mapping = self.UNBORN_SOLO_BY_COUNT if solo else self.UNBORN_SHARED_BY_COUNT
            tuning_id = mapping[count]
        else:
            target_age = age_key(target)
            tuning_id = (
                self.INFANT_SOLO_RABBIT_HOLE_ID
                if target_age in ("baby", "infant")
                else self.RABBIT_HOLE_BY_AGE[target_age]
            )
        rabbit_hole_type = self._rabbit_hole_lookup(tuning_id)
        if rabbit_hole_type is None:
            raise IntegrationUnavailable("Rabbit-hole tuning is unavailable")
        if (
            transaction.transaction_type == "household_member"
            and age_key(target) in ("baby", "infant")
        ):
            def after_pickup(canceled=False):
                if canceled:
                    on_finished(True)
                    return
                try:
                    self._start_rabbit_hole(
                        actor,
                        target,
                        rabbit_hole_type,
                        True,
                        on_finished,
                    )
                except Exception:
                    on_finished(True)

            if not self._infant_pickup(actor, target, after_pickup):
                raise IntegrationUnavailable("Baby pickup could not start")
            return True
        return self._start_rabbit_hole(
            actor, target, rabbit_hole_type, solo, on_finished
        )

    def _start_rabbit_hole(
        self, actor, target, rabbit_hole_type, solo, on_finished
    ):
        service = self._service or self._find_service()
        if solo:
            rabbit_hole_id = service.put_sim_in_managed_rabbithole(
                actor, rabbit_hole_type
            )
        else:
            rabbit_hole_id = service.put_sims_in_shared_rabbithole(
                [actor, target], rabbit_hole_type
            )
        if rabbit_hole_id is None:
            raise IntegrationUnavailable("Rabbit hole could not start")
        def callback(canceled=False, **kwargs):
            pending = _RABBIT_HOLE_CALLBACKS.get(actor.sim_id)
            if pending is not None and pending[0] is callback:
                _RABBIT_HOLE_CALLBACKS.pop(actor.sim_id, None)
            on_finished(canceled)

        _RABBIT_HOLE_CALLBACKS[actor.sim_id] = (
            callback,
            service._get_rabbit_hole(actor.sim_id, rabbit_hole_id),
        )
        try:
            service.set_rabbit_hole_expiration_callback(
                actor.sim_id,
                rabbit_hole_id,
                callback,
            )
        except Exception:
            _RABBIT_HOLE_CALLBACKS.pop(actor.sim_id, None)
            service.remove_sim_from_rabbit_hole(
                actor.sim_id, rabbit_hole_id, canceled=True
            )
            raise
        return True

    def _queue_infant_pickup(self, actor, target, callback):
        import services
        import sims4.resources
        from interactions.context import InteractionContext
        from interactions.priority import Priority

        target_age = age_key(target)

        def failed(reason):
            self._logger.log(
                "baby_pickup_failed",
                reason=reason,
                target_age=target_age,
                target_id=str(target.sim_id),
            )
            return False

        actor_sim = actor.get_sim_instance()
        target_sim = target.get_sim_instance()
        if target_sim is None and target_age == "baby":
            target_sim = services.object_manager().get(target.sim_id)
        if actor_sim is None:
            return failed("actor_unavailable")
        if target_sim is None:
            return failed("target_unavailable")
        carrier = getattr(target_sim, "parent", None)
        if target_age == "baby":
            def queue_hold(*_):
                affordance = services.get_instance_manager(
                    sims4.resources.Types.INTERACTION
                ).get(self.NEWBORN_HOLD_AFFORDANCE_ID)
                if affordance is None:
                    callback(True)
                    return
                context = InteractionContext(
                    actor_sim,
                    InteractionContext.SOURCE_SCRIPT,
                    Priority.High,
                )
                result = actor_sim.push_super_affordance(
                    affordance, target_sim, context
                )
                if not result or result.interaction.is_finishing:
                    callback(True)
                    return
                parent = getattr(target_sim, "parent", None)
                self._logger.log(
                    "newborn_hold_queued",
                    parent_id=(
                        str(parent.sim_id)
                        if getattr(parent, "sim_id", None) is not None
                        else None
                    ),
                    parent_is_actor=parent is actor_sim,
                    target_id=str(target.sim_id),
                )

                def hold_finished(interaction):
                    parent = getattr(target_sim, "parent", None)
                    self._logger.log(
                        "newborn_hold_finished",
                        finishing_naturally=(
                            interaction.is_finishing_naturally
                        ),
                        held_actions_active=any(
                            getattr(
                                getattr(active, "affordance", None),
                                "guid64",
                                None,
                            ) == 275181
                            for active in getattr(actor_sim, "si_state", ())
                        ),
                        parent_id=(
                            str(parent.sim_id)
                            if getattr(parent, "sim_id", None) is not None
                            else None
                        ),
                        parent_is_actor=parent is actor_sim,
                        target_id=str(target.sim_id),
                    )
                    callback(
                        not (
                            interaction.is_finishing_naturally
                            and target_sim.parent is actor_sim
                        )
                    )

                result.interaction.register_on_finishing_callback(
                    hold_finished
                )

            if carrier is actor_sim:
                callback(False)
                return True
            if getattr(carrier, "is_sim", False):
                held_interaction = next(
                    (
                        interaction
                        for interaction in carrier.si_state
                        if getattr(interaction, "target", None) is target_sim
                    ),
                    None,
                )
                if held_interaction is None:
                    return failed("carrier_interaction_unavailable")
                held_interaction.register_on_finishing_callback(queue_hold)
                if not held_interaction.cancel_user(
                    cancel_reason_msg="Shady Sim Deals newborn handoff"
                ):
                    return failed("carrier_release_rejected")
                return True
            queue_hold()
            return True
        if getattr(carrier, "is_sim", False) and carrier is not actor_sim:
            source_sim = carrier
            interaction_target = actor_sim
            affordance_id = self.INFANT_HANDOFF_AFFORDANCE_ID
            interaction_kwargs = {}
        else:
            source_sim = actor_sim
            interaction_target = target_sim
            affordance_id = self.INFANT_PICKUP_AFFORDANCE_ID
            interaction_kwargs = {}
        affordance = services.get_instance_manager(
            sims4.resources.Types.INTERACTION
        ).get(affordance_id)
        if affordance is None:
            return failed("affordance_unavailable")
        context = InteractionContext(
            source_sim, InteractionContext.SOURCE_SCRIPT, Priority.High
        )
        if affordance_id == self.INFANT_HANDOFF_AFFORDANCE_ID:
            context.carry_target = target_sim
        result = source_sim.push_super_affordance(
            affordance, interaction_target, context, **interaction_kwargs
        )
        if not result:
            return failed("interaction_rejected")
        if result.interaction.is_finishing:
            return failed("interaction_finished_during_startup")

        def pickup_finished(interaction):
            completed = (
                interaction.is_finishing_naturally
                and target_sim.parent is actor_sim
            )
            callback(not completed)

        result.interaction.register_on_finishing_callback(pickup_finished)
        return True

    @staticmethod
    def _find_service():
        import services

        return services.get_rabbit_hole_service()

    @staticmethod
    def _find_rabbit_hole(instance_id):
        import services
        import sims4.resources

        return services.get_instance_manager(
            sims4.resources.Types.RABBIT_HOLE
        ).get(instance_id)


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
            if not self._switch_household(manager, sim_info, source, holdings):
                raise RuntimeError("native household switch was rejected")
            if sim_info in source.sim_infos or sim_info not in holdings.sim_infos:
                raise RuntimeError("household membership did not change")
        except Exception as exc:
            if sim_info not in source.sim_infos:
                try:
                    if sim_info in holdings.sim_infos:
                        if not self._switch_household(
                            manager, sim_info, holdings, source
                        ):
                            raise RuntimeError(
                                "native household rollback was rejected"
                            )
                    else:
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
        if not self._switch_household(manager, sim_info, holdings, source):
            raise IntegrationUnavailable("Transfer rollback was rejected")
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
        if self._household_manager is not None:
            return self._household_manager
        import services

        return services.household_manager()

    @staticmethod
    def _switch_household(manager, sim_info, source, destination):
        from sims.household_enums import HouseholdChangeOrigin

        return manager.switch_sim_from_household_to_target_household(
            sim_info,
            source,
            destination,
            destroy_if_empty_household=False,
            reason=HouseholdChangeOrigin.UNKNOWN,
        )

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
