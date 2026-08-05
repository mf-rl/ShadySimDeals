import json
import struct
import xml.etree.ElementTree as ET

import build_mod


EXPECTED_RESOURCE_KEYS = {
    (0xE882D22F, 0, 0xEAA1200000000001),
    (0xE882D22F, 0, 0xEAA21FFB1081E002),
    (0xE882D22F, 0, 0xEAA21FFB1081E003),
    (0xE882D22F, 0, 0xEAA21FFB1081E004),
    (0xB16AD2FA, 0, 0xEAA21FFB1081E005),
    (0xB16AD2FA, 0, 0xEAA21FFB1081E006),
    (0xB16AD2FA, 0, 0xEAA21FFB1081E007),
    (0xE882D22F, 0, 0xEAA21FFB1081E008),
    (0xE882D22F, 0, 0xEAA21FFB1081E009),
    (0xE882D22F, 0, 0xEAA21FFB1081E00A),
    (0xB16AD2FA, 0, 0xEAA21FFB1081E00B),
    (0xB16AD2FA, 0, 0xEAA21FFB1081E00C),
    (0xB16AD2FA, 0, 0xEAA21FFB1081E00D),
    (0xB16AD2FA, 0, 0xEAA21FFB1081E00E),
    (0xB16AD2FA, 0, 0xEAA21FFB1081E00F),
    (0xB16AD2FA, 0, 0xEAA21FFB1081E010),
    (0xE882D22F, 0, 0xEAA21FFB1081E011),
    (0xE882D22F, 0, 0xEAA21FFB1081E012),
    (0xE882D22F, 0, 0xEAA21FFB1081E013),
    (0x03E9D964, 0x80000000, 0xEAA1200000000010),
    (0x545AC67A, 0x00E9D967, 0xEAA1200000000010),
    (0x7DF2169C, 0, 0xEAA1200000000020),
    (0x220557DA, 0x80000000, 0x00A1100000000001),
}


def packaged_interactions():
    return {
        instance: ET.fromstring(data)
        for data, resource_type, _, instance in build_mod.package_resources()
        if resource_type == build_mod.INTERACTION_TUNING_TYPE
    }


def test_localized_money_tokens_have_no_control_character_prefix():
    strings = json.loads(
        (build_mod.ROOT / "localization" / "en_us.json").read_text(
            encoding="utf-8"
        )
    )
    money_strings = tuple(text for text in strings.values() if "{0.Money}" in text)

    assert money_strings
    assert all(not any(ord(character) < 32 for character in text) for text in money_strings)
    assert all("7{0.Money}" not in text for text in money_strings)


def test_build_stbl_encodes_version_five_table():
    data = build_mod.build_stbl({0xA1100001: "ShadySimDeals"})

    magic, version, compressed, count, unused, total_size = struct.unpack_from(
        "<4sHBQ2sI", data
    )
    key, flags, size = struct.unpack_from("<IBH", data, 21)

    assert (magic, version, compressed, count, unused) == (
        b"STBL",
        5,
        0,
        1,
        b"\0\0",
    )
    assert total_size == len("ShadySimDeals".encode("utf-8")) + 1
    assert (key, flags, size) == (0xA1100001, 0, 13)
    assert data[28:] == b"ShadySimDeals"


def test_package_resources_include_every_planned_resource():
    resources = build_mod.package_resources()
    keys = {(resource_type, group, instance) for _, resource_type, group, instance in resources}

    assert keys == EXPECTED_RESOURCE_KEYS


def test_household_rabbit_holes_pair_participants_with_timed_affordances():
    resources = build_mod.package_resources()
    rabbit_holes = {
        instance: ET.fromstring(data)
        for data, resource_type, _, instance in resources
        if resource_type == build_mod.RABBIT_HOLE_TYPE
        and 0xEAA21FFB1081E005 <= instance <= 0xEAA21FFB1081E007
    }
    interactions = packaged_interactions()
    expected = {
        0xEAA21FFB1081E005: (0xEAA21FFB1081E008, 75),
        0xEAA21FFB1081E006: (0xEAA21FFB1081E009, 90),
        0xEAA21FFB1081E007: (0xEAA21FFB1081E00A, 120),
    }

    assert set(rabbit_holes) == set(expected)
    for rabbit_hole_id, (affordance_id, minutes) in expected.items():
        rabbit_hole = rabbit_holes[rabbit_hole_id]
        assert rabbit_hole.attrib["c"] == "TwoSimRabbitHole"
        assert rabbit_hole.attrib["m"] == "rabbit_hole.multi_sim_rabbit_hole"
        assert int(rabbit_hole.find("./T[@n='affordance']").text) == affordance_id
        assert rabbit_hole.find("./L[@n='first_participant_types']/E").text == "Actor"
        assert rabbit_hole.find("./L[@n='second_participant_types']/E").text == "PickedSim"

        interaction = interactions[affordance_id]
        assert interaction.find("./V[@n='_saveable']").attrib["t"] == "disabled"
        condition = interaction.find(
            "./V[@n='basic_content']/U/L[@n='conditional_actions']"
            "/V/U/L[@n='conditions']/V[@t='time_based']/U"
        )
        liabilities = interaction.findall(
            "./L[@n='basic_liabilities']/V"
        )
        assert [liability.attrib["t"] for liability in liabilities] == [
            "hide_sim_liability"
        ]
        assert interaction.find("./E[@n='target_type']").text == "ACTOR"
        assert int(condition.find("./T[@n='min_time']").text) == minutes
        assert int(condition.find("./T[@n='max_time']").text) == minutes
        action = interaction.find(
            "./V[@n='basic_content']/U/L[@n='conditional_actions']/V/U/E[@n='interaction_action']"
        )
        assert action.text == "EXIT_NATURALLY"


def test_unborn_rabbit_holes_package_solo_shared_and_timed_resources():
    resources = build_mod.package_resources()
    rabbit_holes = {
        instance: ET.fromstring(data)
        for data, resource_type, _, instance in resources
        if resource_type == build_mod.RABBIT_HOLE_TYPE
        and 0xEAA21FFB1081E00B <= instance <= 0xEAA21FFB1081E010
    }
    interactions = packaged_interactions()
    expected = {
        0xEAA21FFB1081E00B: ("RabbitHole", 0xEAA21FFB1081E011, 90),
        0xEAA21FFB1081E00C: ("TwoSimRabbitHole", 0xEAA21FFB1081E011, 90),
        0xEAA21FFB1081E00D: ("RabbitHole", 0xEAA21FFB1081E012, 120),
        0xEAA21FFB1081E00E: ("TwoSimRabbitHole", 0xEAA21FFB1081E012, 120),
        0xEAA21FFB1081E00F: ("RabbitHole", 0xEAA21FFB1081E013, 150),
        0xEAA21FFB1081E010: ("TwoSimRabbitHole", 0xEAA21FFB1081E013, 150),
    }

    assert set(rabbit_holes) == set(expected)
    for rabbit_hole_id, (class_name, affordance_id, minutes) in expected.items():
        rabbit_hole = rabbit_holes[rabbit_hole_id]
        assert rabbit_hole.attrib["c"] == class_name
        assert int(rabbit_hole.find("./T[@n='affordance']").text) == affordance_id
        if class_name == "RabbitHole":
            assert rabbit_hole.attrib["m"] == "rabbit_hole.rabbit_hole"
        else:
            assert rabbit_hole.attrib["m"] == "rabbit_hole.multi_sim_rabbit_hole"
            assert rabbit_hole.find("./L[@n='first_participant_types']/E").text == "Actor"
            assert rabbit_hole.find("./L[@n='second_participant_types']/E").text == "PickedSim"

        interaction = interactions[affordance_id]
        assert interaction.find("./V[@n='_saveable']").attrib["t"] == "disabled"
        liabilities = interaction.findall(
            "./L[@n='basic_liabilities']/V"
        )
        assert [liability.attrib["t"] for liability in liabilities] == [
            "hide_sim_liability"
        ]
        assert interaction.find("./T[@n='display_name']").text == "0xA110000B"
        condition = interaction.find(
            "./V[@n='basic_content']/U/L[@n='conditional_actions']"
            "/V/U/L[@n='conditions']/V[@t='time_based']/U"
        )
        assert int(condition.find("./T[@n='min_time']").text) == minutes
        assert int(condition.find("./T[@n='max_time']").text) == minutes


def test_phone_sales_use_verified_phone_browse_content():
    interactions = packaged_interactions()
    for instance in (0xEAA1200000000001, 0xEAA21FFB1081E002):
        xml = interactions[instance]
        content = xml.find("./V[@n='basic_content']/U/V[@n='content']")
        timer = xml.find(
            "./V[@n='basic_content']/U/L[@n='conditional_actions']"
            "/V/U/L[@n='conditions']/V/U"
        )
        assert content.attrib["t"] == "looping_content"
        assert int(
            content.find("./U/U[@n='animation_ref']/T[@n='factory']").text
        ) == 11701
        assert int(
            content.find(
                ".//L[@n='props']/U/U[@n='value']/T[@n='definition']"
            ).text
        ) == 62464
        assert (
            int(timer.find("./T[@n='min_time']").text),
            int(timer.find("./T[@n='max_time']").text),
        ) == (5, 5)
        assert xml.find("./E[@n='target_type']").text == "ACTOR"
        assert int(
            xml.find("./V[@n='super_affordance_compatibility']/T").text
        ) == 76418


def test_computer_sales_use_verified_computer_browse_content():
    interactions = packaged_interactions()
    for instance in (0xEAA21FFB1081E003, 0xEAA21FFB1081E004):
        xml = interactions[instance]
        content = xml.find("./V[@n='basic_content']/U/V[@n='content']")
        links = {
            int(node.text)
            for node in content.findall(".//L[@n='affordance_links']/T")
        }
        assert content.attrib["t"] == "staging_content"
        assert links == {13188, 13189, 99858}
        assert int(
            xml.find("./V[@n='canonical_animation']/U/T[@n='factory']").text
        ) == 31395
        assert xml.find("./E[@n='target_type']").text == "OBJECT"
        assert int(
            xml.find("./V[@n='super_affordance_compatibility']/T").text
        ) == 77330
        assert int(
            xml.find("./L[@n='test_globals']/V/U/T[@n='value']").text
        ) == 15080
        state_changes = xml.findall(
            "./L[@n='basic_extras']/V[@t='state_change']/U"
        )
        assert [
            int(node.find(".//T[@n='new_value']").text)
            for node in state_changes
        ] == [15103, 15106]
        assert (
            state_changes[0].find("./V[@n='timing']").attrib["t"]
            == "immediately"
        )
        end_timing = state_changes[1].find("./V[@n='timing']")
        assert end_timing.attrib["t"] == "at_end"
        assert (
            end_timing.find("./U/E[@n='criticality']").text
            == "OnCancelOrException"
        )


def test_tuning_xml_ids_match_packaged_instances_and_references():
    resources = build_mod.package_resources()
    interactions = {
        instance: ET.fromstring(data)
        for data, resource_type, _, instance in resources
        if resource_type == build_mod.INTERACTION_TUNING_TYPE
    }
    injector_data, _, _, injector_id = next(
        resource
        for resource in resources
        if resource[1] == build_mod.SNIPPET_TYPE
    )
    injector = ET.fromstring(injector_data)

    assert all(int(xml.attrib["s"]) == instance for instance, xml in interactions.items())
    assert int(injector.attrib["s"]) == injector_id
    phone_ids = {
        int(node.text)
        for node in injector.findall(".//L[@n='phone_affordances']/T")
    }
    assert phone_ids == {
        int("EAA1200000000001", 16),
        int("EAA21FFB1081E002", 16),
    }


def test_lot51_injector_targets_computers_with_computer_interaction():
    injector_data = next(
        data
        for data, resource_type, _, _ in build_mod.package_resources()
        if resource_type == build_mod.SNIPPET_TYPE
    )
    injector = ET.fromstring(injector_data)
    computer_entry = injector.find("./L[@n='inject_by_object_tags']/U")

    assert computer_entry.find("./L[@n='tags']/E").text == "Func_Computer"
    computer_ids = {
        int(node.text)
        for node in computer_entry.findall("./L[@n='affordances']/T")
    }
    assert computer_ids == {
        int("EAA21FFB1081E003", 16),
        int("EAA21FFB1081E004", 16),
    }


def test_phone_interaction_uses_matching_custom_category_resources():
    resources = build_mod.package_resources()
    interaction_data = next(
        data for data, resource_type, _, _ in resources
        if resource_type == 0xE882D22F
    )
    category_data = next(
        data for data, resource_type, _, _ in resources
        if resource_type == 0x03E9D964
    )
    simdata = next(
        data for data, resource_type, _, _ in resources
        if resource_type == 0x545AC67A
    )

    interaction = ET.fromstring(interaction_data)
    category = ET.fromstring(category_data)

    assert int(interaction.find("./T[@n='category']").text) == build_mod.CUSTOM_CATEGORY_ID
    assert int(category.attrib["s"]) == build_mod.CUSTOM_CATEGORY_ID
    assert category.find("./T[@n='_display_name']").text == "0xA1100001"
    assert simdata.startswith(b"DATA\x01\x01\x00\x00")
    assert b"PieMenuCategory\0" in simdata
    assert b"ShadySimDeals:phoneCategory\0" in simdata


def test_unborn_interactions_use_shady_sim_deals_category():
    interactions = {
        instance: ET.fromstring(data)
        for data, resource_type, _, instance in build_mod.package_resources()
        if resource_type == build_mod.INTERACTION_TUNING_TYPE
        and instance in {0xEAA21FFB1081E002, 0xEAA21FFB1081E004}
    }

    assert set(interactions) == {0xEAA21FFB1081E002, 0xEAA21FFB1081E004}
    assert all(
        int(xml.find("./T[@n='category']").text) == build_mod.CUSTOM_CATEGORY_ID
        for xml in interactions.values()
    )


def test_category_simdata_has_verified_schema_and_values():
    simdata = next(
        data for data, resource_type, _, _ in build_mod.package_resources()
        if resource_type == 0x545AC67A
    )
    _, version, table_relative, table_count, schema_relative, schema_count, _ = (
        struct.unpack_from("<4sIiIiII", simdata)
    )
    table_offset = 8 + table_relative
    schema_offset = 16 + schema_relative
    row_pointer_position = table_offset + 20
    row_relative, row_count = struct.unpack_from("<iI", simdata, row_pointer_position)
    row_offset = row_pointer_position + row_relative

    assert (version, table_count, schema_count) == (0x101, 1, 1)
    assert struct.unpack_from("<I", simdata, schema_offset + 8)[0] == 0x022065C1
    assert struct.unpack_from("<I", simdata, table_offset + 16)[0] == 56
    assert row_count == 1
    assert struct.unpack_from("<B", simdata, row_offset)[0] == 0
    assert struct.unpack_from("<I", simdata, row_offset + 4)[0] == 0xA1100001
    assert struct.unpack_from("<i", simdata, row_offset + 8)[0] == 8
    assert struct.unpack_from("<QII", simdata, row_offset + 16) == (
        0x6189CED9570B8609,
        0x00B2D882,
        0,
    )


def test_built_package_index_contains_every_planned_resource(tmp_path):
    target = tmp_path / "ShadySimDeals.package"
    build_mod.build_tuning_package(target)
    data = target.read_bytes()
    resource_count, index_offset, _ = struct.unpack_from("<III", data, 36)
    keys = set()
    offset = index_offset + 4
    for _ in range(resource_count):
        resource_type, group, high, low = struct.unpack_from("<IIII", data, offset)
        keys.add((resource_type, group, (high << 32) | low))
        offset += 32

    assert keys == EXPECTED_RESOURCE_KEYS
