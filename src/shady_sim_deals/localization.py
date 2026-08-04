"""Stable string keys and IDs reserved for the English STBL."""

STRING_IDS = {
    "app_name": 0xA1100001,
    "sell_household_member": 0xA1100002,
    "sell_unborn_nooboo": 0xA1100003,
    "confirmation_title": 0xA1100004,
    "confirmation_body": 0xA1100005,
    "complete_deal": 0xA1100006,
    "develop_morals": 0xA1100007,
    "failure_title": 0xA1100008,
    "failure_body": 0xA1100009,
    "household_rabbit_hole": 0xA110000A,
    "unborn_rabbit_hole": 0xA110000B,
    "completion_household_title": 0xA110000C,
    "completion_household_body": 0xA110000D,
    "completion_unborn_title": 0xA110000E,
    "completion_unborn_body": 0xA110000F,
    "integration_unavailable": 0xA1100010,
    "picker_title": 0xA1100011,
    "picker_body": 0xA1100012,
    "no_eligible_targets": 0xA1100013,
    "lot51_missing": 0xA1100014,
    "holding_rollback_failed": 0xA1100015,
    "unborn_picker_title": 0xA1100016,
    "unborn_picker_body": 0xA1100017,
}


def localized_string(key, *tokens):
    """Create a localized game string without embedding visible English in Python."""
    from sims4.localization import _create_localized_string

    return _create_localized_string(STRING_IDS[key], *tokens)
