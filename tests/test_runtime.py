from shady_sim_deals import sims4_runtime
from shady_sim_deals.orchestrator import TransactionOrchestrator
from shady_sim_deals.pricing import SimSalePricingService


class FakeAge:
    def __init__(self, name="YOUNGADULT"):
        self.name = name


class FakeSimInfo:
    def __init__(
        self,
        sim_id=42,
        first_name="Ada",
        last_name="Lovelace",
        age="YOUNGADULT",
        household_id="home",
        is_pet=False,
    ):
        self.sim_id = sim_id
        self.first_name = first_name
        self.last_name = last_name
        self.age = FakeAge(age)
        self.household_id = household_id
        self.is_pet = is_pet


class FakePicker:
    last = None
    factory_arguments = None

    def __init__(self):
        self.rows = []
        self.shown = False

    @staticmethod
    def TunableFactory():
        class Factory:
            def default(self, **kwargs):
                FakePicker.factory_arguments = kwargs
                FakePicker.last = FakePicker()
                return FakePicker.last

        return Factory()

    def add_row(self, row):
        self.rows.append(row)

    def show_dialog(self, on_response):
        self.shown = True
        self.on_response = on_response


class FakePregnancies:
    def __init__(self, pregnant_ids=(), counts=None):
        self.pregnant_ids = {str(sim_id) for sim_id in pregnant_ids}
        self.counts = counts or {}

    def is_pregnant(self, sim_id):
        return str(sim_id) in self.pregnant_ids

    def expected_offspring_count(self, sim_id):
        return self.counts.get(str(sim_id), 1)


def test_build_sale_candidate_uses_verified_age_only():
    candidate = sims4_runtime.build_sale_candidate(FakeSimInfo())

    assert candidate.sim_id == "42"
    assert candidate.name == "Ada Lovelace"
    assert candidate.age == "young_adult"
    assert candidate.traits == ()
    assert candidate.skills == ()
    assert candidate.fame_level == 0
    assert candidate.occults == ()
    assert candidate.career_level == 0
    assert candidate.education == "none"


def test_eligible_household_member_ids_apply_shared_picker_rules():
    sim_infos = (
        FakeSimInfo("actor", age="ADULT"),
        FakeSimInfo("valid", age="TEEN"),
        FakeSimInfo("child", age="CHILD"),
        FakeSimInfo("pet", age="ADULT", is_pet=True),
        FakeSimInfo("sold", age="ELDER"),
        FakeSimInfo("reserved", age="ADULT"),
        FakeSimInfo("elsewhere", age="ADULT", household_id="other"),
    )

    assert sims4_runtime.eligible_household_member_ids(
        sim_infos,
        actor_id="actor",
        household_id="home",
        sold_check=lambda sim_id: sim_id == "sold",
        reserved_check=lambda sim_id: sim_id == "reserved",
    ) == ("valid",)


class RuntimeRecorder:
    def __init__(self, events):
        self.events = events

    def validate(self, transaction):
        return None

    def reserve(self, transaction):
        self.events.append("reserve")

    def release(self, transaction):
        self.events.append("release")

    def run(self, transaction):
        self.events.append("rabbit_hole")

    def process(self, transaction):
        self.events.append("target")

    def deposit(self, household_id, amount):
        self.events.append(("payment", household_id, amount))

    def apply(self, transaction):
        self.events.append("consequences")


def test_complete_household_sale_uses_shared_transaction_workflow():
    events = []
    recorder = RuntimeRecorder(events)
    workflow = TransactionOrchestrator(
        recorder, recorder, recorder, recorder, recorder, recorder
    )
    target = FakeSimInfo("target", age="ADULT")

    transaction = sims4_runtime.complete_household_sale(
        actor_id="actor",
        target_id="target",
        household_id="home",
        sim_info_lookup=lambda sim_id: target,
        workflow=workflow,
        pricing=SimSalePricingService(),
    )

    assert transaction.state == "completed"
    assert transaction.offer.amount == 4000
    assert events.index("target") < events.index(("payment", "home", 4000))


def test_unborn_candidates_include_pregnant_actor_and_household_member():
    sims = (
        FakeSimInfo("actor"),
        FakeSimInfo("pregnant"),
        FakeSimInfo("not-pregnant"),
        FakeSimInfo("elsewhere", household_id="other"),
    )
    pregnancies = FakePregnancies(("actor", "pregnant", "elsewhere"))

    assert sims4_runtime.eligible_unborn_ids(
        sims,
        household_id="home",
        pregnancy_check=pregnancies.is_pregnant,
        sold_check=lambda sim_id: False,
        reserved_check=lambda sim_id: False,
    ) == ("actor", "pregnant")


def test_build_unborn_candidate_uses_public_offspring_count():
    target = FakeSimInfo("pregnant")
    pregnancies = FakePregnancies(("pregnant",), {"pregnant": 2})

    candidate = sims4_runtime.build_unborn_candidate(target, pregnancies)

    assert candidate.age == "unborn"
    assert candidate.expected_offspring == 2


def test_complete_unborn_sale_uses_unborn_pricing_and_workflow():
    events = []
    recorder = RuntimeRecorder(events)
    recorder.requires_prepayment = True
    recorder.withdraw = lambda household_id, amount: events.append(
        ("refund", household_id, amount)
    )
    workflow = TransactionOrchestrator(
        recorder, recorder, recorder, recorder, recorder, recorder
    )
    target = FakeSimInfo("pregnant")
    pregnancies = FakePregnancies(("pregnant",), {"pregnant": 2})

    deal = sims4_runtime.complete_unborn_sale(
        "actor",
        "pregnant",
        "home",
        lambda sim_id: target,
        pregnancies,
        workflow,
        SimSalePricingService(),
    )

    assert deal.state == "completed"
    assert deal.offer.amount == 27000


def test_confirm_if_accepted_runs_only_for_ok_response():
    calls = []
    dialog = type("Dialog", (), {"response": 0})()

    sims4_runtime.confirm_if_accepted(dialog, calls.append, "target", ok_response=1)
    assert calls == []

    dialog.response = 1
    sims4_runtime.confirm_if_accepted(dialog, calls.append, "target", ok_response=1)
    assert calls == ["target"]


def test_empty_household_still_opens_zero_row_picker(monkeypatch):
    actor_info = FakeSimInfo(sim_id=42)
    actor = type(
        "Actor",
        (),
        {
            "sim_id": 42,
            "household": type(
                "Household",
                (),
                {"id": "home", "sim_infos": (actor_info,)},
            )(),
        },
    )()
    never = type(
        "Never",
        (),
        {"is_sold": lambda self, sim_id: False, "is_reserved": lambda self, sim_id: False},
    )()
    monkeypatch.setattr(sims4_runtime, "UiSimPicker", FakePicker)
    monkeypatch.setattr(
        sims4_runtime,
        "_runtime_services",
        lambda: {"sold": never, "reservations": never},
    )
    interaction = object.__new__(sims4_runtime.PhoneSellHouseholdMemberInteraction)
    interaction.sim = actor
    interaction.get_resolver = lambda: "resolver"

    list(interaction._run_interaction_gen(None))

    assert FakePicker.last is not None
    assert FakePicker.factory_arguments == {"owner": actor, "resolver": "resolver"}
    assert FakePicker.last.shown is True
    assert FakePicker.last.rows == []
    assert FakePicker.last.min_selectable == 1
    assert FakePicker.last.max_selectable == 1


def test_phone_and_computer_household_sales_share_one_implementation():
    shared = sims4_runtime._HouseholdMemberSaleInteraction

    assert issubclass(sims4_runtime.PhoneSellHouseholdMemberInteraction, shared)
    assert issubclass(sims4_runtime.ComputerSellHouseholdMemberInteraction, shared)
    assert "_run_interaction_gen" not in (
        sims4_runtime.PhoneSellHouseholdMemberInteraction.__dict__
    )
    assert "_run_interaction_gen" not in (
        sims4_runtime.ComputerSellHouseholdMemberInteraction.__dict__
    )


def test_phone_and_computer_unborn_sales_share_one_implementation():
    shared = sims4_runtime._UnbornSaleInteraction

    assert issubclass(sims4_runtime.PhoneSellUnbornNoobooInteraction, shared)
    assert issubclass(sims4_runtime.ComputerSellUnbornNoobooInteraction, shared)


def test_unborn_picker_includes_pregnant_actor(monkeypatch):
    FakePicker.last = None
    actor_info = FakeSimInfo(sim_id=42)
    actor = type(
        "Actor",
        (),
        {
            "sim_id": 42,
            "household": type(
                "Household", (), {"id": "home", "sim_infos": (actor_info,)}
            )(),
        },
    )()
    never = type(
        "Never",
        (),
        {
            "is_sold": lambda self, sim_id: False,
            "is_reserved": lambda self, sim_id: False,
        },
    )()
    pregnancies = FakePregnancies((42,))
    monkeypatch.setattr(sims4_runtime, "UiSimPicker", FakePicker)
    monkeypatch.setattr(
        sims4_runtime,
        "SimPickerRow",
        lambda sim_id, tag: type("Row", (), {"sim_id": sim_id, "tag": tag})(),
    )
    monkeypatch.setattr(
        sims4_runtime,
        "_runtime_services",
        lambda: {
            "sold": never,
            "reservations": never,
            "pregnancies": pregnancies,
        },
    )
    interaction = object.__new__(sims4_runtime.PhoneSellUnbornNoobooInteraction)
    interaction.sim = actor
    interaction.get_resolver = lambda: "resolver"

    list(interaction._run_interaction_gen(None))

    assert [row.tag for row in FakePicker.last.rows] == ["42"]


def test_computer_household_sale_opens_shared_picker(monkeypatch):
    FakePicker.last = None
    actor_info = FakeSimInfo(sim_id=42)
    actor = type(
        "Actor",
        (),
        {
            "sim_id": 42,
            "household": type(
                "Household", (), {"id": "home", "sim_infos": (actor_info,)}
            )(),
        },
    )()
    never = type(
        "Never",
        (),
        {
            "is_sold": lambda self, sim_id: False,
            "is_reserved": lambda self, sim_id: False,
        },
    )()
    monkeypatch.setattr(sims4_runtime, "UiSimPicker", FakePicker)
    monkeypatch.setattr(
        sims4_runtime,
        "_runtime_services",
        lambda: {"sold": never, "reservations": never},
    )
    interaction = object.__new__(
        sims4_runtime.ComputerSellHouseholdMemberInteraction
    )
    interaction.sim = actor
    interaction.get_resolver = lambda: "resolver"

    list(interaction._run_interaction_gen(None))

    assert FakePicker.last.shown is True
    assert FakePicker.last.rows == []


def test_notification_uses_tuned_factory_defaults(monkeypatch):
    calls = {}

    class Dialog:
        def show_dialog(self):
            calls["shown"] = True

    dialog = Dialog()

    class Factory:
        def default(self, **kwargs):
            calls["default"] = kwargs
            return dialog

    class Notification:
        @staticmethod
        def TunableFactory():
            calls["factory"] = True
            return Factory()

    monkeypatch.setattr(sims4_runtime, "UiDialogNotification", Notification)

    sims4_runtime._show_notification(
        owner="owner",
        resolver="resolver",
        title_key="failure_title",
        text_key="failure_body",
    )

    assert calls["factory"] is True
    assert calls["default"] == {"owner": "owner", "resolver": "resolver"}
    assert callable(dialog.title)
    assert callable(dialog.text)
    assert calls["shown"] is True


def test_picker_response_looks_up_selected_row_tag(monkeypatch):
    lookups = []
    target = FakeSimInfo(sim_id="target")

    def find_sim_info(sim_id):
        lookups.append(sim_id)
        return target

    class Confirmation:
        def __init__(self, owner, resolver):
            pass

        def show_dialog(self, on_response):
            self.on_response = on_response

    monkeypatch.setattr(
        sims4_runtime.Sims4TransactionValidator,
        "_find_sim_info",
        staticmethod(find_sim_info),
    )
    monkeypatch.setattr(
        sims4_runtime,
        "_runtime_services",
        lambda: {"pricing": SimSalePricingService()},
    )
    monkeypatch.setattr(sims4_runtime, "UiDialogOkCancel", Confirmation)
    interaction = object.__new__(sims4_runtime.PhoneSellHouseholdMemberInteraction)
    interaction.sim = "owner"
    interaction.get_resolver = lambda: "resolver"
    row = type("Row", (), {"tag": "target", "option_id": "wrong"})()
    dialog = type("Dialog", (), {"get_result_rows": lambda self: (row,)})()

    interaction._on_picker_response(dialog)

    assert lookups == ["target"]


def test_offer_confirmation_uses_tuned_factory_defaults(monkeypatch):
    calls = {}
    target = FakeSimInfo(sim_id="target")

    class ConfirmationDialog:
        def show_dialog(self, on_response):
            calls["shown"] = True
            self.on_response = on_response

    confirmation = ConfirmationDialog()

    class Factory:
        def default(self, **kwargs):
            calls["default"] = kwargs
            return confirmation

    class Confirmation:
        @staticmethod
        def TunableFactory():
            calls["factory"] = True
            return Factory()

    monkeypatch.setattr(
        sims4_runtime.Sims4TransactionValidator,
        "_find_sim_info",
        staticmethod(lambda sim_id: target),
    )
    monkeypatch.setattr(
        sims4_runtime,
        "_runtime_services",
        lambda: {"pricing": SimSalePricingService()},
    )
    monkeypatch.setattr(sims4_runtime, "UiDialogOkCancel", Confirmation)
    interaction = object.__new__(sims4_runtime.PhoneSellHouseholdMemberInteraction)
    interaction.sim = "owner"
    interaction.get_resolver = lambda: "resolver"
    row = type("Row", (), {"tag": "target", "option_id": "target"})()
    dialog = type("Dialog", (), {"get_result_rows": lambda self: (row,)})()

    interaction._on_picker_response(dialog)

    assert calls["factory"] is True
    assert calls["default"] == {"owner": "owner", "resolver": "resolver"}
    assert calls["shown"] is True
