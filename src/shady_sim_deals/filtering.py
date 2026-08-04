"""Shared picker candidate filtering."""

from . import config


def _safe_candidate(record, household_id):
    return (
        record.valid
        and record.household_id == str(household_id)
        and not record.sold
        and not record.reserved
        and not record.is_pet
    )


def household_member_candidates(records, actor_id, household_id):
    actor_id = str(actor_id)
    return tuple(
        record
        for record in records
        if record.sim_id != actor_id
        and record.age in config.HOUSEHOLD_SALE_AGES
        and _safe_candidate(record, household_id)
    )


def unborn_candidates(records, household_id):
    return tuple(
        record
        for record in records
        if record.pregnant and _safe_candidate(record, household_id)
    )
