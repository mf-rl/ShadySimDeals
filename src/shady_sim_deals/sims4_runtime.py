"""Thin Sims 4 interaction entry points."""

from types import SimpleNamespace

from .localization import localized_string
from .logging import ModLogger
from .filtering import household_member_candidates, unborn_candidates
from .models import BuyerContext, SaleCandidate, SaleTransaction, SimRecord
from .orchestrator import TransactionOrchestrator
from .pricing import SimSalePricingService
from .processors import HouseholdMemberTargetProcessor, UnbornTargetProcessor
from .registry import SoldSimRegistry, TransactionRegistry
from .sims4_adapters import (
    Sims4FundsAdapter,
    Sims4HouseholdAdapter,
    Sims4PregnancyAdapter,
    Sims4TransactionValidator,
    age_key,
)

LOGGER = ModLogger()
RUNTIME = {}


def build_sale_candidate(sim_info):
    return SaleCandidate(
        sim_info.sim_id,
        "{} {}".format(sim_info.first_name, sim_info.last_name).strip(),
        age_key(sim_info),
    )


def eligible_household_member_ids(
    sim_infos, actor_id, household_id, sold_check, reserved_check
):
    records = []
    for sim_info in sim_infos:
        sim_id = str(sim_info.sim_id)
        try:
            age = age_key(sim_info)
        except ValueError:
            continue
        records.append(
            SimRecord(
                sim_id,
                sim_info.household_id,
                age=age,
                valid=not getattr(sim_info, "is_dying", False)
                and not getattr(sim_info, "is_destroyed", False),
                sold=sold_check(sim_id),
                reserved=reserved_check(sim_id),
                is_pet=getattr(sim_info, "is_pet", False),
            )
        )
    return tuple(
        record.sim_id
        for record in household_member_candidates(records, actor_id, household_id)
    )


def eligible_unborn_ids(
    sim_infos, household_id, pregnancy_check, sold_check, reserved_check
):
    records = []
    for sim_info in sim_infos:
        sim_id = str(sim_info.sim_id)
        try:
            pregnant = bool(pregnancy_check(sim_id))
        except Exception:
            continue
        records.append(
            SimRecord(
                sim_id,
                sim_info.household_id,
                pregnant=pregnant,
                valid=not getattr(sim_info, "is_dying", False)
                and not getattr(sim_info, "is_destroyed", False),
                sold=sold_check(sim_id),
                reserved=reserved_check(sim_id),
                is_pet=getattr(sim_info, "is_pet", False),
            )
        )
    return tuple(
        record.sim_id
        for record in unborn_candidates(records, household_id)
    )


def build_unborn_candidate(sim_info, pregnancy_adapter):
    return SaleCandidate(
        sim_info.sim_id,
        "{} {}".format(sim_info.first_name, sim_info.last_name).strip(),
        "unborn",
        expected_offspring=pregnancy_adapter.expected_offspring_count(
            sim_info.sim_id
        ),
    )


def complete_household_sale(
    actor_id, target_id, household_id, sim_info_lookup, workflow, pricing
):
    target = sim_info_lookup(str(target_id))
    if target is None:
        raise ValueError("Target no longer exists")
    offer = pricing.calculate_household_member_offer(
        build_sale_candidate(target), BuyerContext()
    )
    transaction = SaleTransaction(
        "household_member", actor_id, target_id, household_id
    )
    if workflow.prepare(transaction, offer):
        workflow.confirm_and_complete(transaction)
    return transaction


def complete_unborn_sale(
    actor_id,
    target_id,
    household_id,
    sim_info_lookup,
    pregnancy_adapter,
    workflow,
    pricing,
):
    target = sim_info_lookup(str(target_id))
    if target is None:
        raise ValueError("Target no longer exists")
    offer = pricing.calculate_unborn_offer(
        build_unborn_candidate(target, pregnancy_adapter), BuyerContext()
    )
    transaction = SaleTransaction("unborn", actor_id, target_id, household_id)
    if workflow.prepare(transaction, offer):
        workflow.confirm_and_complete(transaction)
    return transaction


def confirm_if_accepted(dialog, on_confirm, target_id, ok_response):
    if dialog.response == ok_response:
        on_confirm(target_id)

try:
    from interactions.base.super_interaction import SuperInteraction
    from sims4.utils import flexmethod
    from ui.ui_dialog import ButtonType, UiDialogOkCancel
    from ui.ui_dialog_notification import UiDialogNotification
    from ui.ui_dialog_picker import SimPickerRow, UiSimPicker
except ImportError:
    ButtonType = None
    SimPickerRow = None
    UiDialogNotification = None
    UiDialogOkCancel = None
    UiSimPicker = None

    class SuperInteraction:
        pass

    def flexmethod(function):
        return function


def _runtime_services():
    if RUNTIME:
        return RUNTIME
    reservations = TransactionRegistry()
    sold = SoldSimRegistry()
    households = Sims4HouseholdAdapter()
    pregnancies = Sims4PregnancyAdapter()
    funds = Sims4FundsAdapter()
    validator = Sims4TransactionValidator(
        reservation_check=reservations.is_reserved,
    )
    unborn_validator = Sims4TransactionValidator(
        reservation_check=reservations.is_reserved,
        pregnancy_check=pregnancies.is_pregnant,
    )
    target_processor = HouseholdMemberTargetProcessor(
        households,
        SimpleNamespace(apply=lambda transaction: "hidden"),
        sold,
    )
    workflow = TransactionOrchestrator(
        validator,
        reservations,
        SimpleNamespace(run=lambda transaction: None),
        target_processor,
        funds,
        SimpleNamespace(apply=lambda transaction: None),
    )
    unborn_workflow = TransactionOrchestrator(
        unborn_validator,
        reservations,
        SimpleNamespace(run=lambda transaction: None),
        UnbornTargetProcessor(pregnancies),
        funds,
        SimpleNamespace(apply=lambda transaction: None),
    )
    RUNTIME.update(
        reservations=reservations,
        sold=sold,
        workflow=workflow,
        unborn_workflow=unborn_workflow,
        pregnancies=pregnancies,
        pricing=SimSalePricingService(),
    )
    return RUNTIME


def _dialog_text(key, *tokens):
    return lambda *args, **kwargs: localized_string(key, *tokens)


def _show_notification(owner, resolver, title_key, text_key, *tokens):
    dialog = UiDialogNotification.TunableFactory().default(
        owner=owner,
        resolver=resolver,
    )
    dialog.title = _dialog_text(title_key)
    dialog.text = _dialog_text(text_key, *tokens)
    dialog.show_dialog()


class _ShadySimDealsInteraction(SuperInteraction):
    entry_point = "unknown"
    transaction_type = "unknown"
    string_key = "integration_unavailable"

    @flexmethod
    def get_name(cls, inst, *args, **kwargs):
        return localized_string(cls.string_key)

    def _run_interaction_gen(self, timeline):
        yield from ()
        LOGGER.log(
            "integration_unavailable",
            entry_point=self.entry_point,
            transaction_type=self.transaction_type,
        )
        # The interaction intentionally performs no mutation until picker, registration,
        # rabbit-hole, and pregnancy APIs are verified against game tuning.
        return False


class _HouseholdMemberSaleInteraction(_ShadySimDealsInteraction):
    transaction_type = "household_member"
    string_key = "sell_household_member"

    def _run_interaction_gen(self, timeline):
        yield from ()
        try:
            runtime = _runtime_services()
            household = self.sim.household
            candidate_ids = eligible_household_member_ids(
                household.sim_infos,
                self.sim.sim_id,
                household.id,
                runtime["sold"].is_sold,
                runtime["reservations"].is_reserved,
            )
            picker = UiSimPicker.TunableFactory().default(
                owner=self.sim,
                resolver=self.get_resolver(),
            )
            picker.title = _dialog_text("picker_title")
            picker.text = _dialog_text("picker_body")
            picker.max_selectable = 1
            picker.min_selectable = 1
            for candidate_id in candidate_ids:
                picker.add_row(
                    SimPickerRow(sim_id=int(candidate_id), tag=str(candidate_id))
                )
            picker.show_dialog(on_response=self._on_picker_response)
            LOGGER.log("picker_opened", candidate_count=len(candidate_ids))
            return True
        except Exception:
            LOGGER.exception("picker_failed")
            return False

    def _on_picker_response(self, dialog):
        try:
            rows = dialog.get_result_rows()
            if not rows:
                LOGGER.log("picker_cancelled")
                return
            target_id = str(rows[0].tag)
            runtime = _runtime_services()
            target = Sims4TransactionValidator._find_sim_info(target_id)
            candidate = build_sale_candidate(target)
            offer = runtime["pricing"].calculate_household_member_offer(
                candidate, BuyerContext()
            )
            confirmation = UiDialogOkCancel.TunableFactory().default(
                owner=self.sim,
                resolver=self.get_resolver(),
            )
            confirmation.title = _dialog_text("confirmation_title")
            confirmation.text = _dialog_text(
                "confirmation_body", offer.amount, target
            )
            confirmation.text_ok = _dialog_text("complete_deal")
            confirmation.text_cancel = _dialog_text("develop_morals")
            confirmation.show_dialog(
                on_response=lambda response: confirm_if_accepted(
                    response,
                    self._complete_sale,
                    target_id,
                    ButtonType.DIALOG_RESPONSE_OK,
                )
            )
            LOGGER.log(
                "offer_calculated",
                target_id=target_id,
                amount=offer.amount,
                breakdown=offer.breakdown,
            )
        except Exception:
            LOGGER.exception("offer_dialog_failed")

    def _complete_sale(self, target_id):
        try:
            household = self.sim.household
            transaction = complete_household_sale(
                self.sim.sim_id,
                target_id,
                household.id,
                Sims4TransactionValidator._find_sim_info,
                _runtime_services()["workflow"],
                _runtime_services()["pricing"],
            )
            if transaction.state != "completed":
                raise RuntimeError(transaction.failure_reason or "Transaction failed")
            target = Sims4TransactionValidator._find_sim_info(target_id)
            _show_notification(
                self.sim,
                self.get_resolver(),
                "completion_household_title",
                "completion_household_body",
                transaction.offer.amount,
                target,
            )
            LOGGER.log(
                "transaction_completed",
                transaction_id=transaction.transaction_id,
                target_id=target_id,
                amount=transaction.offer.amount,
            )
        except Exception:
            LOGGER.exception("transaction_failed", target_id=str(target_id))
            _show_notification(
                self.sim,
                self.get_resolver(),
                "failure_title",
                "failure_body",
            )


class PhoneSellHouseholdMemberInteraction(_HouseholdMemberSaleInteraction):
    entry_point = "phone"


class _UnbornSaleInteraction(_ShadySimDealsInteraction):
    transaction_type = "unborn"
    string_key = "sell_unborn_nooboo"

    def _run_interaction_gen(self, timeline):
        yield from ()
        try:
            runtime = _runtime_services()
            household = self.sim.household
            candidate_ids = eligible_unborn_ids(
                household.sim_infos,
                household.id,
                runtime["pregnancies"].is_pregnant,
                runtime["sold"].is_sold,
                runtime["reservations"].is_reserved,
            )
            picker = UiSimPicker.TunableFactory().default(
                owner=self.sim,
                resolver=self.get_resolver(),
            )
            picker.title = _dialog_text("unborn_picker_title")
            picker.text = _dialog_text("unborn_picker_body")
            picker.max_selectable = 1
            picker.min_selectable = 1
            for candidate_id in candidate_ids:
                picker.add_row(
                    SimPickerRow(sim_id=int(candidate_id), tag=str(candidate_id))
                )
            picker.show_dialog(on_response=self._on_picker_response)
            LOGGER.log(
                "picker_opened",
                transaction_type="unborn",
                candidate_count=len(candidate_ids),
            )
            return True
        except Exception:
            LOGGER.exception("picker_failed", transaction_type="unborn")
            return False

    def _on_picker_response(self, dialog):
        try:
            rows = dialog.get_result_rows()
            if not rows:
                LOGGER.log("picker_cancelled", transaction_type="unborn")
                return
            target_id = str(rows[0].tag)
            runtime = _runtime_services()
            target = Sims4TransactionValidator._find_sim_info(target_id)
            candidate = build_unborn_candidate(target, runtime["pregnancies"])
            offer = runtime["pricing"].calculate_unborn_offer(
                candidate, BuyerContext()
            )
            confirmation = UiDialogOkCancel.TunableFactory().default(
                owner=self.sim,
                resolver=self.get_resolver(),
            )
            confirmation.title = _dialog_text("confirmation_title")
            confirmation.text = _dialog_text(
                "confirmation_body", offer.amount, target
            )
            confirmation.text_ok = _dialog_text("complete_deal")
            confirmation.text_cancel = _dialog_text("develop_morals")
            confirmation.show_dialog(
                on_response=lambda response: confirm_if_accepted(
                    response,
                    self._complete_sale,
                    target_id,
                    ButtonType.DIALOG_RESPONSE_OK,
                )
            )
            LOGGER.log(
                "offer_calculated",
                transaction_type="unborn",
                target_id=target_id,
                amount=offer.amount,
                breakdown=offer.breakdown,
            )
        except Exception:
            LOGGER.exception("offer_dialog_failed", transaction_type="unborn")

    def _complete_sale(self, target_id):
        try:
            runtime = _runtime_services()
            transaction = complete_unborn_sale(
                self.sim.sim_id,
                target_id,
                self.sim.household.id,
                Sims4TransactionValidator._find_sim_info,
                runtime["pregnancies"],
                runtime["unborn_workflow"],
                runtime["pricing"],
            )
            if transaction.state != "completed":
                raise RuntimeError(
                    transaction.failure_reason or "Transaction failed"
                )
            target = Sims4TransactionValidator._find_sim_info(target_id)
            _show_notification(
                self.sim,
                self.get_resolver(),
                "completion_unborn_title",
                "completion_unborn_body",
                transaction.offer.amount,
                target,
            )
            LOGGER.log(
                "transaction_completed",
                transaction_type="unborn",
                transaction_id=transaction.transaction_id,
                target_id=target_id,
                amount=transaction.offer.amount,
            )
        except Exception:
            LOGGER.exception(
                "transaction_failed",
                transaction_type="unborn",
                target_id=str(target_id),
            )
            _show_notification(
                self.sim,
                self.get_resolver(),
                "failure_title",
                "failure_body",
            )


class PhoneSellUnbornNoobooInteraction(_UnbornSaleInteraction):
    entry_point = "phone"


class ComputerSellHouseholdMemberInteraction(_HouseholdMemberSaleInteraction):
    entry_point = "computer"


class ComputerSellUnbornNoobooInteraction(_UnbornSaleInteraction):
    entry_point = "computer"


def register_interactions():
    LOGGER.log(
        "interaction_registration_delegated",
        dependency="Lot51 Core >=1.43",
    )
    return True


LOGGER.log("mod_initialized", interactions_registered=register_interactions())
