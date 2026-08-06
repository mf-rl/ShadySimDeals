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


def run_generator(generator):
    while True:
        try:
            next(generator)
        except StopIteration as stop:
            return stop.value


def test_build_sale_candidate_uses_verified_age_only():
    candidate = sims4_runtime.build_sale_candidate(
        FakeSimInfo(), FakePregnancies()
    )

    assert candidate.sim_id == "42"
    assert candidate.name == "Ada Lovelace"
    assert candidate.age == "young_adult"
    assert candidate.traits == ()
    assert candidate.skills == ()
    assert candidate.fame_level == 0
    assert candidate.occults == ()
    assert candidate.career_level == 0
    assert candidate.education == "none"
    assert candidate.pregnant is False
    assert candidate.expected_offspring == 1


def test_build_sale_candidate_uses_public_pregnancy_count():
    target = FakeSimInfo("pregnant", age="ADULT")
    pregnancies = FakePregnancies(("pregnant",), {"pregnant": 2})

    candidate = sims4_runtime.build_sale_candidate(target, pregnancies)

    assert candidate.pregnant is True
    assert candidate.expected_offspring == 2


def test_eligible_household_member_ids_apply_shared_picker_rules():
    sim_infos = (
        FakeSimInfo("actor", age="ADULT"),
        FakeSimInfo("baby", age="BABY"),
        FakeSimInfo("infant", age="INFANT"),
        FakeSimInfo("toddler", age="TODDLER"),
        FakeSimInfo("child", age="CHILD"),
        FakeSimInfo("teen", age="TEEN"),
        FakeSimInfo("young-adult", age="YOUNGADULT"),
        FakeSimInfo("adult", age="ADULT"),
        FakeSimInfo("elder", age="ELDER"),
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
    ) == (
        "baby",
        "infant",
        "toddler",
        "child",
        "teen",
        "young-adult",
        "adult",
        "elder",
    )


class RuntimeRecorder:
    def __init__(self, events):
        self.events = events

    def validate(self, transaction, check_reservations=True):
        return None

    def reserve(self, transaction):
        self.events.append("reserve")

    def release(self, transaction):
        self.events.append("release")

    def run(self, transaction, on_finished):
        self.events.append("rabbit_hole")

    def process(self, transaction):
        self.events.append("target")

    def deposit(self, household_id, amount):
        self.events.append(("payment", household_id, amount))

    def apply(self, transaction):
        self.events.append("consequences")


class DelayedWorkflow:
    def prepare(self, transaction, offer):
        transaction.offer = offer
        transaction.state = "offer_calculated"
        return True

    def confirm_and_complete(self, transaction, on_finished=None):
        self.transaction = transaction
        self.callback = on_finished
        transaction.state = "rabbit_hole_started"
        return True

    def finish(self, state, failure_reason=None):
        self.transaction.state = state
        self.transaction.failure_reason = failure_reason
        self.callback(self.transaction)


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


def test_complete_household_sale_reports_prepare_failure():
    completed = []

    class RejectedWorkflow:
        def prepare(self, transaction, offer):
            transaction.offer = offer
            transaction.failure_reason = "Target left the household"
            transaction.state = "failed"
            return False

        def confirm_and_complete(self, transaction, on_finished=None):
            raise AssertionError("rejected transaction cannot be confirmed")

    transaction = sims4_runtime.complete_household_sale(
        actor_id="actor",
        target_id="target",
        household_id="home",
        sim_info_lookup=lambda sim_id: FakeSimInfo("target", age="ADULT"),
        workflow=RejectedWorkflow(),
        pricing=SimSalePricingService(),
        on_finished=completed.append,
    )

    assert completed == [transaction]


def test_complete_pregnant_household_sale_pays_bundle_and_keeps_pregnancy():
    events = []
    recorder = RuntimeRecorder(events)
    workflow = TransactionOrchestrator(
        recorder, recorder, recorder, recorder, recorder, recorder
    )
    target = FakeSimInfo("pregnant", age="ADULT")
    pregnancies = FakePregnancies(("pregnant",))

    transaction = sims4_runtime.complete_household_sale(
        "actor",
        "pregnant",
        "home",
        lambda sim_id: target,
        workflow,
        SimSalePricingService(),
        pregnancies,
    )

    assert transaction.offer.amount == 19000
    assert ("payment", "home", 19000) in events
    assert pregnancies.is_pregnant("pregnant")


def test_household_interaction_notifies_only_after_delayed_completion(monkeypatch):
    notifications = []
    workflow = DelayedWorkflow()
    target = FakeSimInfo("target", age="ADULT")
    actor = type(
        "Actor",
        (),
        {
            "sim_id": "actor",
            "household": type("Household", (), {"id": "home"})(),
        },
    )()
    monkeypatch.setattr(
        sims4_runtime,
        "_runtime_services",
        lambda: {
            "workflow": workflow,
            "pricing": SimSalePricingService(),
            "pregnancies": FakePregnancies(),
        },
    )
    monkeypatch.setattr(
        sims4_runtime.Sims4TransactionValidator,
        "_find_sim_info",
        staticmethod(lambda sim_id: target),
    )
    monkeypatch.setattr(
        sims4_runtime,
        "_show_notification",
        lambda *args: notifications.append(args),
    )
    interaction = object.__new__(
        sims4_runtime.PhoneSellHouseholdMemberInteraction
    )
    interaction.sim = actor
    interaction.get_resolver = lambda: "resolver"

    interaction._complete_sale("target")

    assert notifications == []
    workflow.finish("completed")
    assert notifications[0][2:4] == (
        "completion_household_title",
        "completion_household_body",
    )


def test_household_interaction_reports_delayed_failure(monkeypatch):
    notifications = []
    workflow = DelayedWorkflow()
    target = FakeSimInfo("target", age="ADULT")
    actor = type(
        "Actor",
        (),
        {
            "sim_id": "actor",
            "household": type("Household", (), {"id": "home"})(),
        },
    )()
    monkeypatch.setattr(
        sims4_runtime,
        "_runtime_services",
        lambda: {
            "workflow": workflow,
            "pricing": SimSalePricingService(),
            "pregnancies": FakePregnancies(),
        },
    )
    monkeypatch.setattr(
        sims4_runtime.Sims4TransactionValidator,
        "_find_sim_info",
        staticmethod(lambda sim_id: target),
    )
    monkeypatch.setattr(
        sims4_runtime,
        "_show_notification",
        lambda *args: notifications.append(args),
    )
    monkeypatch.setattr(
        sims4_runtime.LOGGER, "exception", lambda *args, **kwargs: None
    )
    interaction = object.__new__(
        sims4_runtime.PhoneSellHouseholdMemberInteraction
    )
    interaction.sim = actor
    interaction.get_resolver = lambda: "resolver"

    interaction._complete_sale("target")
    workflow.finish("failed", "Rabbit hole was canceled")

    assert notifications[0][2:4] == ("failure_title", "failure_body")


def test_runtime_uses_real_rabbit_holes_for_both_sale_types(monkeypatch):
    monkeypatch.setattr(sims4_runtime, "RUNTIME", {})

    runtime = sims4_runtime._runtime_services()

    assert isinstance(runtime["sold"], sims4_runtime.Sims4SoldSimRegistry)
    assert isinstance(
        runtime["workflow"]._rabbit_holes,
        sims4_runtime.Sims4RabbitHoleAdapter,
    )
    assert isinstance(
        runtime["unborn_workflow"]._rabbit_holes,
        sims4_runtime.Sims4RabbitHoleAdapter,
    )
    assert (
        runtime["unborn_workflow"]._rabbit_holes._expected_offspring_lookup
        == runtime["pregnancies"].expected_offspring_count
    )


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


def test_unborn_sale_waits_for_rabbit_hole_before_pregnancy_and_payment():
    events = []

    class DelayedRabbitHole:
        def run(self, transaction, on_finished):
            events.append("rabbit_hole")
            self.callback = on_finished
            return True

    class Pregnancies(FakePregnancies):
        def conclude_pregnancy(self, sim_id):
            events.append("pregnancy")
            self.pregnant_ids.remove(str(sim_id))
            return True

    rabbit_hole = DelayedRabbitHole()
    recorder = RuntimeRecorder(events)
    pregnancies = Pregnancies(("pregnant",))
    workflow = TransactionOrchestrator(
        recorder,
        recorder,
        rabbit_hole,
        sims4_runtime.UnbornTargetProcessor(pregnancies),
        recorder,
        recorder,
    )
    completed = []

    deal = sims4_runtime.complete_unborn_sale(
        "actor",
        "pregnant",
        "home",
        lambda sim_id: FakeSimInfo("pregnant"),
        pregnancies,
        workflow,
        SimSalePricingService(),
        on_finished=completed.append,
    )

    assert deal.state == "rabbit_hole_started"
    assert "pregnancy" not in events
    assert not any(
        isinstance(event, tuple) and event[0] == "payment" for event in events
    )
    assert completed == []

    rabbit_hole.callback(canceled=False)

    assert deal.state == "completed"
    assert events.index(("payment", "home", 15000)) < events.index("pregnancy")
    assert completed == [deal]


def test_unborn_interaction_notifies_only_after_delayed_completion(monkeypatch):
    notifications = []
    workflow = DelayedWorkflow()
    target = FakeSimInfo("pregnant")
    actor = type(
        "Actor",
        (),
        {"sim_id": "actor", "household": type("Household", (), {"id": "home"})()},
    )()
    monkeypatch.setattr(
        sims4_runtime,
        "_runtime_services",
        lambda: {
            "unborn_workflow": workflow,
            "pricing": SimSalePricingService(),
            "pregnancies": FakePregnancies(("pregnant",)),
        },
    )
    monkeypatch.setattr(
        sims4_runtime.Sims4TransactionValidator,
        "_find_sim_info",
        staticmethod(lambda sim_id: target),
    )
    monkeypatch.setattr(sims4_runtime, "_show_notification", lambda *args: notifications.append(args))
    interaction = object.__new__(sims4_runtime.PhoneSellUnbornNoobooInteraction)
    interaction.sim = actor
    interaction.get_resolver = lambda: "resolver"

    interaction._complete_sale("pregnant")

    assert notifications == []
    workflow.finish("completed")
    assert notifications[0][2:4] == (
        "completion_unborn_title",
        "completion_unborn_body",
    )


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


def test_device_content_finishes_before_picker(monkeypatch):
    events = []

    def run_device(self, timeline):
        events.append("device")
        yield from ()
        return True

    monkeypatch.setattr(
        sims4_runtime.SuperInteraction, "_run_interaction_gen", run_device
    )
    interaction = object.__new__(
        sims4_runtime.PhoneSellHouseholdMemberInteraction
    )
    interaction._open_picker = lambda: events.append("picker") or True

    assert run_generator(interaction._run_interaction_gen(None)) is True
    assert events == ["device", "picker"]


def test_phone_device_exception_logs_and_opens_picker(monkeypatch):
    events = []

    def fail_device(self, timeline):
        yield from ()
        raise RuntimeError("animation failed")

    monkeypatch.setattr(
        sims4_runtime.SuperInteraction, "_run_interaction_gen", fail_device
    )
    monkeypatch.setattr(
        sims4_runtime.LOGGER,
        "exception",
        lambda event, **data: events.append((event, data)),
    )
    interaction = object.__new__(sims4_runtime.PhoneSellUnbornNoobooInteraction)
    interaction._open_picker = lambda: events.append("picker") or True

    assert run_generator(interaction._run_interaction_gen(None)) is True
    assert events[-1] == "picker"
    assert events[0][0] == "device_animation_failed"
    assert events[0][1]["entry_point"] == "phone"


def test_computer_device_failure_suppresses_picker(monkeypatch):
    events = []

    def fail_device(self, timeline):
        yield from ()
        return False

    monkeypatch.setattr(
        sims4_runtime.SuperInteraction, "_run_interaction_gen", fail_device
    )
    monkeypatch.setattr(
        sims4_runtime.LOGGER,
        "log",
        lambda event, **data: events.append((event, data)),
    )
    interaction = object.__new__(
        sims4_runtime.ComputerSellHouseholdMemberInteraction
    )
    interaction._open_picker = lambda: events.append("picker") or True

    assert run_generator(interaction._run_interaction_gen(None)) is False
    assert "picker" not in events
    assert events == [
        ("device_animation_failed", {"entry_point": "computer"})
    ]


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
        lambda: {
            "pricing": SimSalePricingService(),
            "pregnancies": FakePregnancies(),
        },
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
        lambda: {
            "pricing": SimSalePricingService(),
            "pregnancies": FakePregnancies(),
        },
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
