import json
import shutil
import struct
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile

ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = ROOT / "src" / "shady_sim_deals"
DIST = ROOT / "dist"
SCRIPT_TARGET = DIST / "ShadySimDeals.ts4script"
PACKAGE_TARGET = DIST / "ShadySimDeals.package"
TEXCONV_PATH = ROOT / "tools" / "directxtex" / "texconv.exe"
INTERACTION_TUNING_TYPE = 0xE882D22F
RABBIT_HOLE_TYPE = 0xB16AD2FA
TRAIT_TUNING_TYPE = 0xCB5FDDC7
BUFF_TUNING_TYPE = 0x6017E896
PIE_MENU_CATEGORY_TYPE = 0x03E9D964
SIMDATA_TYPE = 0x545AC67A
SNIPPET_TYPE = 0x7DF2169C
STRING_TABLE_TYPE = 0x220557DA
DST_IMAGE_TYPE = 0x00B2D882
CUSTOM_CATEGORY_ID = 0xEAA1200000000010
CATEGORY_XML_GROUP = 0x80000000
CATEGORY_SIMDATA_GROUP = 0x00E9D967
TRAIT_SIMDATA_GROUP = 0x005FDD0C
BUFF_SIMDATA_GROUP = 0x0017E8F6
ICON_RESOURCES = (
    ("icons/Phone-Computer-App/app-icon.png", 0xEAA21FFB1081E01A),
    ("icons/QueueActions/Sell House Member.png", 0xEAA21FFB1081E01B),
    ("icons/QueueActions/Sell Unborn Nooboo.png", 0xEAA21FFB1081E01C),
    ("icons/QueueActions/Attend a Definitely Legal Exchange.png", 0xEAA21FFB1081E01D),
    ("icons/QueueActions/Arrange a Pre-order.png", 0xEAA21FFB1081E01E),
    ("icons/Traits/Family Asset Liquidator.png", 0xEAA21FFB1081E01F),
    ("icons/Traits/Outsourced by My Own Family.png", 0xEAA21FFB1081E020),
    ("icons/Traits/Stork Claim Mysteriously Denied.png", 0xEAA21FFB1081E021),
    ("icons/Moodlets/Quarterly Profits, Fewer Mouths.png", 0xEAA21FFB1081E022),
    ("icons/Moodlets/Apparently, Love Had a Return Policy.png", 0xEAA21FFB1081E023),
    ("icons/Moodlets/The Nursery Has Been Downsized.png", 0xEAA21FFB1081E024),
)


def dxt5_to_dst5(data):
    if len(data) < 128 or data[:4] != b"DDS ":
        raise ValueError("Expected a complete DDS image")
    height, width = struct.unpack_from("<II", data, 12)
    if width < 1 or height < 1:
        raise ValueError("DDS dimensions must be positive")
    if data[84:88] != b"DXT5":
        raise ValueError("Expected DXT5 DDS data")
    if struct.unpack_from("<I", data, 28)[0] != 1:
        raise ValueError("Expected a DDS image with one mip")
    expected_size = 128 + ((width + 3) // 4) * ((height + 3) // 4) * 16
    if len(data) != expected_size:
        raise ValueError("Incomplete or extra DXT5 block data")

    blocks = tuple(
        data[offset:offset + 16]
        for offset in range(128, len(data), 16)
    )
    header = bytearray(data[:128])
    header[84:88] = b"DST5"
    return bytes(header) + b"".join(
        tuple(block[0:2] for block in blocks)
        + tuple(block[8:12] for block in blocks)
        + tuple(block[2:8] for block in blocks)
        + tuple(block[12:16] for block in blocks)
    )


def validate_icon_png(source):
    if not source.is_file():
        raise FileNotFoundError(f"Missing icon source: {source}")
    header = source.read_bytes()[:29]
    if len(header) < 29 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Expected a PNG icon: {source}")
    width, height = struct.unpack_from(">II", header, 16)
    if (width, height) != (256, 256):
        raise ValueError(f"Icon must be 256x256: {source}")
    if tuple(header[24:26]) != (8, 6):
        raise ValueError(f"Icon must be 8-bit RGBA: {source}")


def compile_icon(source, temporary_directory, converter=TEXCONV_PATH):
    validate_icon_png(source)
    if not converter.is_file():
        raise FileNotFoundError(f"Missing texconv executable: {converter}")
    result = subprocess.run(
        (
            str(converter),
            "-nologo",
            "-y",
            "-dx9",
            "-f",
            "BC3_UNORM",
            "-m",
            "1",
            "-o",
            str(temporary_directory),
            str(source),
        ),
        capture_output=True,
        text=True,
    )
    if result.returncode:
        output = "\n".join(part for part in (result.stdout, result.stderr) if part)
        raise RuntimeError(f"texconv failed for {source}: {output}")
    converted = temporary_directory / f"{source.stem}.dds"
    if not converted.is_file():
        raise FileNotFoundError(f"texconv did not produce {converted}")
    return dxt5_to_dst5(converted.read_bytes())


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
        DST_IMAGE_TYPE,
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


def build_trait_simdata(
    table_name, display_name, description, origin_description, icon_instance
):
    columns = (
        ("cas_idle_asm_key", 19, 32),
        ("occults", 14, 128),
        ("ui_category", 21, 176),
        ("display_name", 20, 92),
        ("trait_origin_description", 20, 164),
        ("refresh_sim_thumbnail", 0, 136),
        ("cas_trait_vfx", 11, 80),
        ("cas_trait_hidden", 0, 76),
        ("conflicting_traits", 14, 84),
        ("thumbnail_type_asm_param", 11, 156),
        ("genders", 14, 104),
        ("icon", 19, 112),
        ("cas_allowed_pack", 8, 24),
        ("cas_trait_asm_param", 11, 72),
        ("display_overrides", 14, 96),
        ("bb_filter_tags", 14, 16),
        ("trait_description", 20, 160),
        ("trait_type", 8, 168),
        ("cas_idle_asm_state", 11, 48),
        ("ages", 14, 0),
        ("tags", 14, 148),
        ("cas_selected_icon", 19, 56),
        ("species", 14, 140),
        ("bb_filter_styles", 14, 8),
    )
    table_offset, row_offset, lists_offset = 32, 192, 384
    string_table_offset, schema_offset, column_offset = 456, 464, 488
    data = bytearray(968)
    struct.pack_into(
        "<4sIiIiII", data, 0, b"DATA", 0x101, 24, 4, 448, 1, 0
    )
    struct.pack_into(
        "<iIiIIiI", data, table_offset, 0, _fnv32(table_name), 424,
        13, 184, 140, 1,
    )
    struct.pack_into(
        "<iIiIIiI", data, 60, -0x80000000, _fnv32(""), -0x80000000,
        18, 8, 304, 0,
    )
    struct.pack_into(
        "<iIiIIiI", data, 88, -0x80000000, _fnv32(""), -0x80000000,
        8, 8, 276, 9,
    )
    struct.pack_into(
        "<iIiIIiI", data, 116, -0x80000000, _fnv32(""), -0x80000000,
        1, 1, 320, 6,
    )
    struct.pack_into("<iI", data, row_offset, lists_offset - row_offset, 8)
    none_offset = string_table_offset + 1
    for offset in (48, 72, 80, 156):
        struct.pack_into("<i", data, row_offset + offset, none_offset - (row_offset + offset))
    for offset in (8, 16, 84, 96, 104, 128, 148):
        struct.pack_into("<iI", data, row_offset + offset, -0x80000000, 0)
    struct.pack_into("<I", data, row_offset + 92, display_name)
    struct.pack_into(
        "<QII", data, row_offset + 112, icon_instance, DST_IMAGE_TYPE, 0
    )
    species_offset = lists_offset + 64
    struct.pack_into(
        "<iI", data, row_offset + 140, species_offset - (row_offset + 140), 1
    )
    struct.pack_into("<III", data, row_offset + 160, description, origin_description, 1)
    struct.pack_into("<II", data, row_offset + 176, 0x80000000, 0xC1A03855)
    for index, value in enumerate((8, 32, 1, 4, 2, 64, 16, 128, 1)):
        struct.pack_into("<Q", data, lists_offset + index * 8, value)
    data[string_table_offset:string_table_offset + 6] = b"\0None\0"
    struct.pack_into(
        "<iIIIiI", data, schema_offset, 0, _fnv32("Trait"), 0xC8782638,
        184, 8, len(columns),
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
        "<QII", data, row_offset + 40, icon_instance, DST_IMAGE_TYPE, 0
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


@lru_cache(maxsize=1)
def compiled_icon_resources():
    with tempfile.TemporaryDirectory(prefix="shady-sim-deals-icons-") as directory:
        temporary_directory = Path(directory)
        return tuple(
            (
                compile_icon(ROOT / relative_path, temporary_directory),
                DST_IMAGE_TYPE,
                0,
                instance,
            )
            for relative_path, instance in ICON_RESOURCES
        )


def package_resources():
    strings = json.loads((ROOT / "localization" / "en_us.json").read_text(encoding="utf-8"))
    resources = (
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
                0xA1100018, 0xA1100019, 0xA1100024, 0xEAA21FFB1081E01F,
            ),
            SIMDATA_TYPE, TRAIT_SIMDATA_GROUP, 0xEAA21FFB1081E014,
        ),
        (
            build_trait_simdata(
                "ShadySimDeals_trait_OutsourcedByMyOwnFamily",
                0xA110001A, 0xA110001B, 0xA1100024, 0xEAA21FFB1081E020,
            ),
            SIMDATA_TYPE, TRAIT_SIMDATA_GROUP, 0xEAA21FFB1081E015,
        ),
        (
            build_trait_simdata(
                "ShadySimDeals_trait_StorkClaimMysteriouslyDenied",
                0xA110001C, 0xA110001D, 0xA1100024, 0xEAA21FFB1081E021,
            ),
            SIMDATA_TYPE, TRAIT_SIMDATA_GROUP, 0xEAA21FFB1081E016,
        ),
        (
            build_buff_simdata(
                "ShadySimDeals_buff_QuarterlyProfitsFewerMouths",
                0xA110001E, 0xA110001F, 0xEAA21FFB1081E022, 14640, 4,
            ),
            SIMDATA_TYPE, BUFF_SIMDATA_GROUP, 0xEAA21FFB1081E017,
        ),
        (
            build_buff_simdata(
                "ShadySimDeals_buff_LoveHadAReturnPolicy",
                0xA1100020, 0xA1100021, 0xEAA21FFB1081E023, 14643, 6,
            ),
            SIMDATA_TYPE, BUFF_SIMDATA_GROUP, 0xEAA21FFB1081E018,
        ),
        (
            build_buff_simdata(
                "ShadySimDeals_buff_NurseryHasBeenDownsized",
                0xA1100022, 0xA1100023, 0xEAA21FFB1081E024, 14643, 10,
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
                0xEAA21FFB1081E01A,
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
            (
                ROOT
                / "tuning"
                / "interactions"
                / "newborn_pickup.xml"
            ).read_bytes(),
            INTERACTION_TUNING_TYPE,
            0,
            0xEAA21FFB1081E025,
        ),
        (
            build_stbl({int(key, 16): value for key, value in strings.items()}),
            STRING_TABLE_TYPE,
            0x80000000,
            0x00A1100000000001,
        ),
    )
    return resources + compiled_icon_resources()


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
