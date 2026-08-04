import json
import struct
import xml.etree.ElementTree as ET

import build_mod


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


def test_package_resources_include_phone_and_computer_sales():
    resources = build_mod.package_resources()
    keys = {(resource_type, group, instance) for _, resource_type, group, instance in resources}

    assert keys == {
        (0xE882D22F, 0, 0xEAA1200000000001),
        (0xE882D22F, 0, 0xEAA21FFB1081E002),
        (0xE882D22F, 0, 0xEAA21FFB1081E003),
        (0xE882D22F, 0, 0xEAA21FFB1081E004),
        (0x03E9D964, 0x80000000, 0xEAA1200000000010),
        (0x545AC67A, 0x00E9D967, 0xEAA1200000000010),
        (0x7DF2169C, 0, 0xEAA1200000000020),
        (0x220557DA, 0x80000000, 0x00A1100000000001),
    }


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

    assert keys == {
        (0xE882D22F, 0, 0xEAA1200000000001),
        (0xE882D22F, 0, 0xEAA21FFB1081E002),
        (0xE882D22F, 0, 0xEAA21FFB1081E003),
        (0xE882D22F, 0, 0xEAA21FFB1081E004),
        (0x03E9D964, 0x80000000, 0xEAA1200000000010),
        (0x545AC67A, 0x00E9D967, 0xEAA1200000000010),
        (0x7DF2169C, 0, 0xEAA1200000000020),
        (0x220557DA, 0x80000000, 0x00A1100000000001),
    }
