import json
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile

ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = ROOT / "src" / "shady_sim_deals"
DIST = ROOT / "dist"
SCRIPT_TARGET = DIST / "ShadySimDeals.ts4script"
PACKAGE_TARGET = DIST / "ShadySimDeals.package"
INTERACTION_TUNING_TYPE = 0xE882D22F
RABBIT_HOLE_TYPE = 0xB16AD2FA
TRAIT_TUNING_TYPE = 0xCB5FDDC7
BUFF_TUNING_TYPE = 0x6017E896
PIE_MENU_CATEGORY_TYPE = 0x03E9D964
SIMDATA_TYPE = 0x545AC67A
SNIPPET_TYPE = 0x7DF2169C
STRING_TABLE_TYPE = 0x220557DA
CUSTOM_CATEGORY_ID = 0xEAA1200000000010
CATEGORY_XML_GROUP = 0x80000000
CATEGORY_SIMDATA_GROUP = 0x00E9D967
TRAIT_SIMDATA_GROUP = 0x005FDD0C
BUFF_SIMDATA_GROUP = 0x0017E8F6


def build_stbl(entries):
    encoded = tuple(
        (int(key), str(value).encode("utf-8"))
        for key, value in sorted(entries.items())
    )
    data = bytearray(
        struct.pack(
            "<4sHBQ2sI",
            b"STBL",
            5,
            0,
            len(encoded),
            b"\0\0",
            sum(len(value) + 1 for _, value in encoded),
        )
    )
    for key, value in encoded:
        data += struct.pack("<IBH", key, 0, len(value))
        data += value
    return bytes(data)


def _fnv32(value):
    result = 0x811C9DC5
    for byte in value.lower().encode("utf-8"):
        result = ((result * 0x01000193) ^ byte) & 0xFFFFFFFF
    return result


def build_pie_menu_category_simdata(
    table_name, display_name_key, display_priority, icon_instance
):
    columns = (
        ("_collapsible", 0, 0),
        ("_display_name", 20, 4),
        ("_display_priority", 6, 8),
        ("_icon", 19, 16),
        ("_parent", 18, 32),
        ("_special_category", 8, 40),
        ("mood_overrides", 14, 48),
    )
    table_offset = 32
    row_offset = 64
    schema_offset = 128
    column_offset = 160
    string_offset = 304
    data = bytearray(string_offset)

    struct.pack_into(
        "<4sIiIiII",
        data,
        0,
        b"DATA",
        0x101,
        table_offset - 8,
        1,
        schema_offset - 16,
        1,
        0x80000000,
    )
    struct.pack_into(
        "<iIiIIiI",
        data,
        table_offset,
        0,
        _fnv32(table_name),
        schema_offset - (table_offset + 8),
        13,
        56,
        row_offset - (table_offset + 20),
        1,
    )
    struct.pack_into("<B", data, row_offset, 0)
    struct.pack_into("<I", data, row_offset + 4, display_name_key)
    struct.pack_into("<i", data, row_offset + 8, display_priority)
    struct.pack_into(
        "<QII",
        data,
        row_offset + 16,
        icon_instance,
        0x00B2D882,
        0,
    )
    struct.pack_into("<Q", data, row_offset + 32, 0)
    struct.pack_into("<Q", data, row_offset + 40, 0)
    struct.pack_into("<iI", data, row_offset + 48, -0x80000000, 0)
    struct.pack_into(
        "<iIIIiI",
        data,
        schema_offset,
        0,
        _fnv32("PieMenuCategory"),
        0x022065C1,
        56,
        column_offset - (schema_offset + 16),
        len(columns),
    )
    for index, (name, data_type, field_offset) in enumerate(columns):
        offset = column_offset + index * 20
        struct.pack_into(
            "<iIHHIi",
            data,
            offset,
            0,
            _fnv32(name),
            data_type,
            0,
            field_offset,
            -0x80000000,
        )

    pointers = [(table_offset, table_name), (schema_offset, "PieMenuCategory")]
    pointers.extend(
        (column_offset + index * 20, name)
        for index, (name, _, _) in enumerate(columns)
    )
    for pointer_offset, value in pointers:
        encoded = value.encode("utf-8") + b"\0"
        struct.pack_into("<i", data, pointer_offset, len(data) - pointer_offset)
        data.extend(encoded)
    return bytes(data)


def _append_simdata_strings(data, pointers):
    for pointer_offset, value in pointers:
        struct.pack_into("<i", data, pointer_offset, len(data) - pointer_offset)
        data.extend(value.encode("utf-8") + b"\0")
    return bytes(data)


def build_trait_simdata(table_name, display_name, description, icon_instance):
    columns = (
        ("cas_idle_asm_key", 19, 8),
        ("ui_category", 21, 120),
        ("display_name", 20, 60),
        ("trait_origin_description", 20, 108),
        ("conflicting_traits", 14, 52),
        ("genders", 14, 64),
        ("icon", 19, 72),
        ("cas_trait_asm_param", 11, 48),
        ("trait_description", 20, 104),
        ("trait_type", 8, 112),
        ("cas_idle_asm_state", 11, 24),
        ("ages", 14, 0),
        ("tags", 14, 96),
        ("cas_selected_icon", 19, 32),
        ("species", 14, 88),
    )
    table_offset, row_offset, lists_offset = 32, 128, 256
    string_table_offset, schema_offset, column_offset = 328, 336, 368
    data = bytearray(672)
    struct.pack_into(
        "<4sIiIiII", data, 0, b"DATA", 0x101, 24, 3, 320, 1, 0
    )
    struct.pack_into(
        "<iIiIIiI", data, table_offset, 0, _fnv32(table_name), 296,
        13, 128, 76, 1,
    )
    struct.pack_into(
        "<iIiIIiI", data, 60, -0x80000000, _fnv32(""), -0x80000000,
        8, 8, 176, 9,
    )
    struct.pack_into(
        "<iIiIIiI", data, 88, -0x80000000, _fnv32(""), -0x80000000,
        1, 1, 220, 6,
    )
    struct.pack_into("<iI", data, row_offset, 128, 8)
    struct.pack_into("<i", data, row_offset + 24, 176)
    struct.pack_into("<i", data, row_offset + 48, 153)
    for offset in (52, 64, 96):
        struct.pack_into("<iI", data, row_offset + offset, -0x80000000, 0)
    struct.pack_into("<I", data, row_offset + 60, display_name)
    struct.pack_into(
        "<QII", data, row_offset + 72, icon_instance, 0x00B2D882, 0
    )
    struct.pack_into("<iI", data, row_offset + 88, 104, 1)
    struct.pack_into("<I", data, row_offset + 104, description)
    struct.pack_into("<I", data, row_offset + 108, 0x80000000)
    struct.pack_into("<I", data, row_offset + 112, 1)
    struct.pack_into("<II", data, row_offset + 120, 0x80000000, 0xC1A03855)
    for index, value in enumerate((8, 32, 1, 4, 2, 64, 16, 128, 1)):
        struct.pack_into("<Q", data, lists_offset + index * 8, value)
    data[string_table_offset:string_table_offset + 6] = b"\0None\0"
    struct.pack_into(
        "<iIIIiI", data, schema_offset, 0, _fnv32("Trait"), 0x6CBEA9DB,
        128, 8, len(columns),
    )
    for index, (name, data_type, field_offset) in enumerate(columns):
        offset = column_offset + index * 20
        struct.pack_into(
            "<iIHHIi", data, offset, 0, _fnv32(name), data_type, 0,
            field_offset, -0x80000000,
        )
    pointers = [(table_offset, table_name), (schema_offset, "Trait")]
    pointers.extend(
        (column_offset + index * 20, name)
        for index, (name, _, _) in enumerate(columns)
    )
    return _append_simdata_strings(data, pointers)


def build_buff_simdata(
    table_name, name, description, icon_instance, mood_type, mood_weight
):
    columns = (
        ("audio_sting_on_remove", 19, 16),
        ("mood_type", 18, 56),
        ("icon", 19, 40),
        ("buff_description", 20, 32),
        ("buff_name", 20, 36),
        ("mood_weight", 6, 64),
        ("timeout_string", 20, 68),
        ("ui_sort_order", 6, 72),
        ("audio_sting_on_add", 19, 0),
    )
    table_offset, row_offset, schema_offset, column_offset = 32, 128, 208, 232
    data = bytearray(416)
    struct.pack_into(
        "<4sIiIiII", data, 0, b"DATA", 0x101, 24, 1, 192, 1, 0
    )
    struct.pack_into(
        "<iIiIIiI", data, table_offset, 0, _fnv32(table_name), 168,
        13, 80, 76, 1,
    )
    struct.pack_into(
        "<QII", data, row_offset, 0x8AF8B916CF64C646, 0x39B2AA4A, 0
    )
    struct.pack_into(
        "<QII", data, row_offset + 16, 0x3BF33216A25546EA, 0x39B2AA4A, 0
    )
    struct.pack_into("<II", data, row_offset + 32, description, name)
    struct.pack_into(
        "<QII", data, row_offset + 40, icon_instance, 0x00B2D882, 0
    )
    struct.pack_into("<Q", data, row_offset + 56, mood_type)
    struct.pack_into("<iIi", data, row_offset + 64, mood_weight, 0, 1)
    struct.pack_into(
        "<iIIIiI", data, schema_offset, 0, _fnv32("Buff"), 0x71722956,
        80, 8, len(columns),
    )
    for index, (column_name, data_type, field_offset) in enumerate(columns):
        offset = column_offset + index * 20
        struct.pack_into(
            "<iIHHIi", data, offset, 0, _fnv32(column_name), data_type, 0,
            field_offset, -0x80000000,
        )
    pointers = [(table_offset, table_name), (schema_offset, "Buff")]
    pointers.extend(
        (column_offset + index * 20, column_name)
        for index, (column_name, _, _) in enumerate(columns)
    )
    return _append_simdata_strings(data, pointers)


def package_resources():
    strings = json.loads((ROOT / "localization" / "en_us.json").read_text(encoding="utf-8"))
    return (
        (
            (ROOT / "tuning" / "interactions" / "phone_sell_household_member.xml").read_bytes(),
            INTERACTION_TUNING_TYPE,
            0,
            0xEAA1200000000001,
        ),
        (
            (
                ROOT
                / "tuning"
                / "interactions"
                / "phone_sell_unborn_nooboo.xml"
            ).read_bytes(),
            INTERACTION_TUNING_TYPE,
            0,
            0xEAA21FFB1081E002,
        ),
        (
            (
                ROOT
                / "tuning"
                / "interactions"
                / "computer_sell_household_member.xml"
            ).read_bytes(),
            INTERACTION_TUNING_TYPE,
            0,
            0xEAA21FFB1081E003,
        ),
        (
            (
                ROOT
                / "tuning"
                / "interactions"
                / "computer_sell_unborn_nooboo.xml"
            ).read_bytes(),
            INTERACTION_TUNING_TYPE,
            0,
            0xEAA21FFB1081E004,
        ),
        (
            (ROOT / "tuning" / "rabbit_holes" / "household_sale_elder.xml").read_bytes(),
            RABBIT_HOLE_TYPE,
            0,
            0xEAA21FFB1081E005,
        ),
        (
            (ROOT / "tuning" / "rabbit_holes" / "household_sale_child.xml").read_bytes(),
            RABBIT_HOLE_TYPE,
            0,
            0xEAA21FFB1081E006,
        ),
        (
            (ROOT / "tuning" / "rabbit_holes" / "household_sale_adult.xml").read_bytes(),
            RABBIT_HOLE_TYPE,
            0,
            0xEAA21FFB1081E007,
        ),
        (
            (ROOT / "tuning" / "interactions" / "household_rabbit_hole_75.xml").read_bytes(),
            INTERACTION_TUNING_TYPE,
            0,
            0xEAA21FFB1081E008,
        ),
        (
            (ROOT / "tuning" / "interactions" / "household_rabbit_hole_90.xml").read_bytes(),
            INTERACTION_TUNING_TYPE,
            0,
            0xEAA21FFB1081E009,
        ),
        (
            (ROOT / "tuning" / "interactions" / "household_rabbit_hole_120.xml").read_bytes(),
            INTERACTION_TUNING_TYPE,
            0,
            0xEAA21FFB1081E00A,
        ),
        (
            (ROOT / "tuning" / "rabbit_holes" / "unborn_sale_solo_90.xml").read_bytes(),
            RABBIT_HOLE_TYPE,
            0,
            0xEAA21FFB1081E00B,
        ),
        (
            (ROOT / "tuning" / "rabbit_holes" / "unborn_sale_shared_90.xml").read_bytes(),
            RABBIT_HOLE_TYPE,
            0,
            0xEAA21FFB1081E00C,
        ),
        (
            (ROOT / "tuning" / "rabbit_holes" / "unborn_sale_solo_120.xml").read_bytes(),
            RABBIT_HOLE_TYPE,
            0,
            0xEAA21FFB1081E00D,
        ),
        (
            (ROOT / "tuning" / "rabbit_holes" / "unborn_sale_shared_120.xml").read_bytes(),
            RABBIT_HOLE_TYPE,
            0,
            0xEAA21FFB1081E00E,
        ),
        (
            (ROOT / "tuning" / "rabbit_holes" / "unborn_sale_solo_150.xml").read_bytes(),
            RABBIT_HOLE_TYPE,
            0,
            0xEAA21FFB1081E00F,
        ),
        (
            (ROOT / "tuning" / "rabbit_holes" / "unborn_sale_shared_150.xml").read_bytes(),
            RABBIT_HOLE_TYPE,
            0,
            0xEAA21FFB1081E010,
        ),
        (
            (ROOT / "tuning" / "interactions" / "unborn_rabbit_hole_90.xml").read_bytes(),
            INTERACTION_TUNING_TYPE,
            0,
            0xEAA21FFB1081E011,
        ),
        (
            (ROOT / "tuning" / "interactions" / "unborn_rabbit_hole_120.xml").read_bytes(),
            INTERACTION_TUNING_TYPE,
            0,
            0xEAA21FFB1081E012,
        ),
        (
            (ROOT / "tuning" / "interactions" / "unborn_rabbit_hole_150.xml").read_bytes(),
            INTERACTION_TUNING_TYPE,
            0,
            0xEAA21FFB1081E013,
        ),
        (
            (ROOT / "tuning" / "traits" / "family_asset_liquidator.xml").read_bytes(),
            TRAIT_TUNING_TYPE,
            0,
            0xEAA21FFB1081E014,
        ),
        (
            (ROOT / "tuning" / "traits" / "outsourced_by_my_own_family.xml").read_bytes(),
            TRAIT_TUNING_TYPE,
            0,
            0xEAA21FFB1081E015,
        ),
        (
            (ROOT / "tuning" / "traits" / "stork_claim_mysteriously_denied.xml").read_bytes(),
            TRAIT_TUNING_TYPE,
            0,
            0xEAA21FFB1081E016,
        ),
        (
            (ROOT / "tuning" / "buffs" / "quarterly_profits_fewer_mouths.xml").read_bytes(),
            BUFF_TUNING_TYPE,
            0,
            0xEAA21FFB1081E017,
        ),
        (
            (ROOT / "tuning" / "buffs" / "love_had_a_return_policy.xml").read_bytes(),
            BUFF_TUNING_TYPE,
            0,
            0xEAA21FFB1081E018,
        ),
        (
            (ROOT / "tuning" / "buffs" / "nursery_has_been_downsized.xml").read_bytes(),
            BUFF_TUNING_TYPE,
            0,
            0xEAA21FFB1081E019,
        ),
        (
            build_trait_simdata(
                "ShadySimDeals_trait_FamilyAssetLiquidator",
                0xA1100018, 0xA1100019, 0x47FFEEDF30C4B115,
            ),
            SIMDATA_TYPE, TRAIT_SIMDATA_GROUP, 0xEAA21FFB1081E014,
        ),
        (
            build_trait_simdata(
                "ShadySimDeals_trait_OutsourcedByMyOwnFamily",
                0xA110001A, 0xA110001B, 0x8B841C91497034A5,
            ),
            SIMDATA_TYPE, TRAIT_SIMDATA_GROUP, 0xEAA21FFB1081E015,
        ),
        (
            build_trait_simdata(
                "ShadySimDeals_trait_StorkClaimMysteriouslyDenied",
                0xA110001C, 0xA110001D, 0x8B841C91497034A5,
            ),
            SIMDATA_TYPE, TRAIT_SIMDATA_GROUP, 0xEAA21FFB1081E016,
        ),
        (
            build_buff_simdata(
                "ShadySimDeals_buff_QuarterlyProfitsFewerMouths",
                0xA110001E, 0xA110001F, 0x2357E4F259B6A63E, 14640, 4,
            ),
            SIMDATA_TYPE, BUFF_SIMDATA_GROUP, 0xEAA21FFB1081E017,
        ),
        (
            build_buff_simdata(
                "ShadySimDeals_buff_LoveHadAReturnPolicy",
                0xA1100020, 0xA1100021, 0x8B841C91497034A5, 14643, 6,
            ),
            SIMDATA_TYPE, BUFF_SIMDATA_GROUP, 0xEAA21FFB1081E018,
        ),
        (
            build_buff_simdata(
                "ShadySimDeals_buff_NurseryHasBeenDownsized",
                0xA1100022, 0xA1100023, 0x8B841C91497034A5, 14643, 10,
            ),
            SIMDATA_TYPE, BUFF_SIMDATA_GROUP, 0xEAA21FFB1081E019,
        ),
        (
            (ROOT / "tuning" / "categories" / "shady_sim_deals_phone.xml").read_bytes(),
            PIE_MENU_CATEGORY_TYPE,
            CATEGORY_XML_GROUP,
            CUSTOM_CATEGORY_ID,
        ),
        (
            build_pie_menu_category_simdata(
                "ShadySimDeals:phoneCategory",
                0xA1100001,
                8,
                0x6189CED9570B8609,
            ),
            SIMDATA_TYPE,
            CATEGORY_SIMDATA_GROUP,
            CUSTOM_CATEGORY_ID,
        ),
        (
            (ROOT / "tuning" / "snippets" / "lot51_phone_injector.xml").read_bytes(),
            SNIPPET_TYPE,
            0,
            0xEAA1200000000020,
        ),
        (
            build_stbl({int(key, 16): value for key, value in strings.items()}),
            STRING_TABLE_TYPE,
            0x80000000,
            0x00A1100000000001,
        ),
    )


def compile_scripts(temporary_directory):
    compiled = []
    for source in sorted(SOURCE_ROOT.glob("*.py")):
        relative = Path("shady_sim_deals") / (source.stem + ".pyc")
        target = temporary_directory / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        command = (
            "import py_compile,sys;"
            "py_compile.compile(sys.argv[1],cfile=sys.argv[2],doraise=True)"
        )
        subprocess.run(
            ["py", "-3.7", "-c", command, str(source), str(target)],
            check=True,
        )
        compiled.append((target, str(relative).replace("\\", "/")))
    return compiled


def build_script_archive(compiled):
    with ZipFile(str(SCRIPT_TARGET), "w", ZIP_STORED) as archive:
        for source, name in compiled:
            archive.write(str(source), name)


def build_tuning_package(target=PACKAGE_TARGET):
    resources = package_resources()
    resource_offset = 96
    index = bytearray()
    payload = bytearray()
    for resource, resource_type, group, instance in resources:
        index += struct.pack(
            "<IIIIIIII",
            resource_type,
            group,
            instance >> 32,
            instance & 0xFFFFFFFF,
            resource_offset + len(payload),
            len(resource) | 0x80000000,
            len(resource),
            0x00010000,
        )
        payload += resource
    index_offset = resource_offset + len(payload)
    header = bytearray(96)
    struct.pack_into("<4sII", header, 0, b"DBPF", 2, 1)
    struct.pack_into("<III", header, 36, len(resources), index_offset, 4 + len(index))
    struct.pack_into("<IQ", header, 60, 3, index_offset)
    target.write_bytes(header + payload + struct.pack("<I", 0) + index)


def main():
    if not shutil.which("py"):
        raise SystemExit("Python launcher not found. Install Python 3.7 and rerun.")
    DIST.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="shady-sim-deals-") as temporary:
        build_script_archive(compile_scripts(Path(temporary)))
    build_tuning_package()
    print("built {} and {}".format(SCRIPT_TARGET, PACKAGE_TARGET))
    print("included ENG_US localization and Lot51 Core phone/computer injection")


if __name__ == "__main__":
    main()
