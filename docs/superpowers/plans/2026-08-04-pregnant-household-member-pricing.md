# Pregnant Household-Member Pricing Implementation Plan

> **Historical note (2026-08-07):** This implementation plan is retained as a development record. Its unchecked boxes describe the original workflow, not current repository status; use [`SPECS_CHECKLIST.md`](../../../SPECS_CHECKLIST.md) for current status.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Add the configured unborn value to a pregnant household member's sale offer while preserving the pregnancy after transfer.

**Architecture:** SaleCandidate records whether the selected Sim is pregnant and the expected offspring count. The shared pricing service adds an unborn special bonus to the normal household-member valuation, while the existing pregnancy adapter supplies runtime state for preview and completion.

**Tech Stack:** Python 3.7-compatible Sims 4 scripts, pytest on Python 3.12, DBPF packaging, Lot51 Core 1.43+

## Global Constraints

- Supported game patch is 1.125.59.1030.
- Game-side Python must remain compatible with Python 3.7.
- Lot51 Core 1.43 or newer remains the only mod dependency.
- Use the pregnancy tracker through Sims4PregnancyAdapter; do not infer pregnancy from moodlets.
- Pregnancy bonuses are deterministic and use the existing offspring multipliers.
- Apply the existing 50,000 ordinary and 100,000 rare offer caps to the combined amount.
- Selling the household member must not clear or alter the pregnancy.

---

### Task 1: Add bundled pregnancy valuation to the pricing domain

**Files:**
- Modify: tests/test_pricing.py
- Modify: src/shady_sim_deals/models.py:42-67
- Modify: src/shady_sim_deals/pricing.py:12-69

**Interfaces:**
- Consumes: config.BASE_PRICES["unborn"] and config.pregnancy_multiplier(expected_offspring).
- Produces: SaleCandidate.pregnant: bool and SaleOffer.breakdown["pregnancy_bonus"]: int.

- [ ] **Step 1: Add failing deterministic pregnancy-pricing tests**

Add these assertions to tests/test_pricing.py:

    def test_pregnant_household_member_includes_unborn_bundle_value():
        service = pricing()
        buyer = BuyerContext()
        expected = ((1, 19000), (2, 31000), (3, 40000))
        for count, amount in expected:
            offer = service.calculate_household_member_offer(
                candidate(
                    "adult",
                    pregnant=True,
                    expected_offspring=count,
                ),
                buyer,
            )
            assert offer.amount == amount
            assert offer.breakdown["pregnancy_bonus"] == amount - 4000


    def test_nonpregnant_household_member_has_no_pregnancy_bonus():
        offer = pricing().calculate_household_member_offer(
            candidate("child"), BuyerContext()
        )
        assert offer.amount == 8000
        assert offer.breakdown["pregnancy_bonus"] == 0


    def test_pregnant_household_member_respects_combined_offer_cap():
        offer = pricing().calculate_household_member_offer(
            candidate(
                "baby",
                pregnant=True,
                expected_offspring=3,
                traits=("genius",),
                fame_level=5,
                occults=("ghost", "vampire"),
            ),
            BuyerContext(demand_multiplier=1.4),
        )
        assert offer.amount == 50000

- [ ] **Step 2: Run pricing tests and verify failure**

Run:

    $env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_pricing.py

Expected: failures because SaleCandidate has no pregnant argument and the breakdown has no pregnancy_bonus.

- [ ] **Step 3: Add the minimum candidate and pricing fields**

Add pregnant=False before expected_offspring in SaleCandidate.__init__, then assign:

    self.pregnant = bool(pregnant)

In calculate_household_member_offer, calculate:

    pregnancy_bonus = 0
    if candidate.pregnant:
        pregnancy_bonus = int(
            config.BASE_PRICES["unborn"]
            * config.pregnancy_multiplier(candidate.expected_offspring)
        )

Pass pregnancy_bonus to _calculate as a new special_bonus argument. Give _calculate special_bonus=0, add it after the existing multiplied Sim value, and include:

    "pregnancy_bonus": int(special_bonus),

in the breakdown. Leave calculate_unborn_offer unchanged except for using the default special bonus.

- [ ] **Step 4: Run pricing tests**

Run:

    $env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_pricing.py

Expected: all pricing tests pass.

- [ ] **Step 5: Commit domain pricing**

    git add src/shady_sim_deals/models.py src/shady_sim_deals/pricing.py tests/test_pricing.py
    git commit -m "feat: value pregnancy in household sales"

### Task 2: Supply pregnancy state to household-sale preview and completion

**Files:**
- Modify: tests/test_runtime.py
- Modify: src/shady_sim_deals/sims4_runtime.py:25-35,100-115,297-335

**Interfaces:**
- Consumes: pregnancy_adapter.is_pregnant(sim_id) -> bool and pregnancy_adapter.expected_offspring_count(sim_id) -> int.
- Produces: build_sale_candidate(sim_info, pregnancy_adapter=None) and complete_household_sale(..., pregnancy_adapter=None).

- [ ] **Step 1: Add failing runtime candidate and transaction tests**

Replace test_build_sale_candidate_uses_verified_age_only with a non-pregnant call that passes FakePregnancies and asserts pregnant is false. Add:

    def test_build_sale_candidate_uses_public_pregnancy_count():
        target = FakeSimInfo("pregnant", age="ADULT")
        pregnancies = FakePregnancies(("pregnant",), {"pregnant": 2})

        candidate = sims4_runtime.build_sale_candidate(target, pregnancies)

        assert candidate.pregnant is True
        assert candidate.expected_offspring == 2

Add a completed transaction test:

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

- [ ] **Step 2: Run runtime tests and verify failure**

Run:

    $env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_runtime.py

Expected: failures because the household candidate and completion functions do not accept the pregnancy adapter.

- [ ] **Step 3: Wire the existing pregnancy adapter through the shared household flow**

Change build_sale_candidate to accept pregnancy_adapter=None. When an adapter is present, call is_pregnant once and call expected_offspring_count only when pregnant. Pass pregnant and expected_offspring into SaleCandidate.

Add pregnancy_adapter=None as the final complete_household_sale argument and pass it to build_sale_candidate.

In _HouseholdMemberSaleInteraction:

- pass runtime["pregnancies"] to build_sale_candidate when calculating the preview;
- pass runtime["pregnancies"] to complete_household_sale when confirming.

Do not call conclude_pregnancy anywhere in the household-member path.

- [ ] **Step 4: Run runtime and full tests**

Run:

    $env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_runtime.py
    $env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests

Expected: all tests pass.

- [ ] **Step 5: Commit runtime wiring**

    git add src/shady_sim_deals/sims4_runtime.py tests/test_runtime.py
    git commit -m "feat: price pregnant household targets"

### Task 3: Document, build, and live-verify

**Files:**
- Modify: README.md
- Modify after live confirmation: SPECS_CHECKLIST.md
- Generated: dist/ShadySimDeals.package
- Generated: dist/ShadySimDeals.ts4script

**Interfaces:**
- Consumes: Tasks 1 and 2.
- Produces: documented, installed, and live-verified bundled pricing.

- [ ] **Step 1: Document the bundled offer rule**

Replace README.md's age-only household offer sentence with a concise rule that normal household-member value receives the configured unborn bonus when the target is pregnant, while the pregnancy stays with the transferred Sim.

- [ ] **Step 2: Run full tests and build**

Run:

    $env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests
    py -3.12 build_mod.py

Expected: all tests pass and both artifacts have fresh timestamps.

- [ ] **Step 3: Install after The Sims 4 is closed**

Run:

    .\install_mod.ps1

Expected: installed artifact hashes match dist.

- [ ] **Step 4: Live-test a singleton pregnant household-member sale**

Verify the offer equals the Sim's normal age price plus 15,000, payment occurs once, the Sim leaves the selectable household, and the pregnancy remains active after transfer.

- [ ] **Step 5: Record confirmed evidence and commit**

Add a checklist entry for deterministic pregnant household-member bundle pricing. Mark only the singleton live case after confirmation; leave twin/triplet live pricing unchecked.

    git add README.md SPECS_CHECKLIST.md
    git commit -m "docs: describe bundled pregnancy pricing"
