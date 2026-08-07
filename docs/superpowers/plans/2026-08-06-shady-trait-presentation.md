# Shady Trait Presentation Implementation Plan

> **Historical note (2026-08-07):** This implementation plan is retained as a development record. Its unchecked boxes describe the original workflow, not current repository status; use [`SPECS_CHECKLIST.md`](../../../SPECS_CHECKLIST.md) for current status.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render the three permanent sale traits with their approved names and descriptions and the shared native origin label **Shady Attribute**.

**Architecture:** Replace the outdated generated Trait SimData layout with the current client Trait schema while leaving runtime sale logic unchanged. XML remains authoritative for the ordinary and gender-neutral display names; client SimData carries the ordinary display name, description, origin description, and native gameplay trait type.

**Tech Stack:** Python 3.12 build/tests, Python 3.7 Sims 4 runtime compatibility, DBPF tuning packages, binary SimData, XML tuning, STBL localization, pytest.

## Global Constraints

- Keep **Family Asset Liquidator**, **Outsourced by My Own Family**, and **Stork Claim Mysteriously Denied** and their approved descriptions unchanged.
- Use **Shady Attribute** as the shared native trait-origin label.
- Traits remain permanent, visible, non-CAS-selectable, and outside personality-trait slots.
- Do not depend on WickedWhims or copy its custom trait-type value.
- Do not change transaction, rabbit-hole, payment, pregnancy, assignment, or moodlet behavior.
- Keep build/runtime code compatible with the project's existing Python versions.

---

### Task 1: Current Trait client schema and Shady origin label

**Files:**
- Modify: `tests/test_build.py:95`
- Modify: `build_mod.py:22-251`
- Modify: `build_mod.py:437-469`
- Modify: `localization/en_us.json:36`
- Modify: `tuning/traits/family_asset_liquidator.xml`
- Modify: `tuning/traits/outsourced_by_my_own_family.xml`
- Modify: `tuning/traits/stork_claim_mysteriously_denied.xml`

**Interfaces:**
- Consumes: `build_mod._fnv32(value: str) -> int`, `build_mod._append_simdata_strings(data: bytearray, pointers) -> bytes`, existing trait tuning IDs `0xEAA21FFB1081E014` through `0xEAA21FFB1081E016`.
- Produces: `build_trait_simdata(table_name: str, display_name: int, description: int, origin_description: int, icon_instance: int) -> bytes` using current Trait schema hash `0xC8782638`, main-row size `184`, and four tables.

- [ ] **Step 1: Write failing client-schema and localization tests**

In `tests/test_build.py`, replace the trait portion of `test_sale_trait_and_buff_simdata_has_client_schema_and_values` with a small parser that resolves the main row and schema columns by name:

```python
def trait_simdata_fields(data):
    _, version, table_relative, table_count, schema_relative, schema_count, _ = (
        struct.unpack_from("<4sIiIiII", data)
    )
    table_offset = 8 + table_relative
    schema_offset = 16 + schema_relative
    table = struct.unpack_from("<iIiIIiI", data, table_offset)
    row_offset = table_offset + 20 + table[5]
    schema = struct.unpack_from("<iIIIiI", data, schema_offset)
    column_offset = schema_offset + 16 + schema[4]
    fields = {}
    for index in range(schema[5]):
        offset = column_offset + index * 20
        pointer, _, data_type, _, field_offset, _ = struct.unpack_from(
            "<iIHHIi", data, offset
        )
        name = data[offset + pointer :].split(b"\0", 1)[0].decode()
        fields[name] = (data_type, row_offset + field_offset)
    return version, table_count, schema_count, table[4], schema[2], fields
```

Assert all three resources carry the approved values and current schema:

```python
expected = {
    0xEAA21FFB1081E014: (0xA1100018, 0xA1100019, 0x47FFEEDF30C4B115),
    0xEAA21FFB1081E015: (0xA110001A, 0xA110001B, 0x8B841C91497034A5),
    0xEAA21FFB1081E016: (0xA110001C, 0xA110001D, 0x8B841C91497034A5),
}
for instance, (name_key, description_key, icon_instance) in expected.items():
    data = resources[(build_mod.TRAIT_SIMDATA_GROUP, instance)]
    version, tables, schemas, row_size, schema_hash, fields = (
        trait_simdata_fields(data)
    )
    assert (version, tables, schemas, row_size, schema_hash) == (
        0x101, 4, 1, 184, 0xC8782638
    )
    assert struct.unpack_from("<I", data, fields["display_name"][1])[0] == name_key
    assert struct.unpack_from("<I", data, fields["trait_description"][1])[0] == description_key
    assert struct.unpack_from("<I", data, fields["trait_origin_description"][1])[0] == 0xA1100024
    assert struct.unpack_from("<I", data, fields["trait_type"][1])[0] == 1
    assert struct.unpack_from("<Q", data, fields["icon"][1])[0] == icon_instance
```

Extend the XML/localization assertions:

```python
assert strings["0xA1100024"] == "Shady Attribute"
for trait in traits.values():
    assert trait.find("./T[@n='display_name']") is not None
    assert trait.find("./T[@n='display_name_gender_neutral']") is not None
    assert trait.find("./T[@n='trait_origin_description']").text == "0xA1100024"
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_build.py -k 'sale_trait_and_buff_simdata or sale_traits_and_moodlets'
```

Expected: FAIL because current Trait SimData has three tables, row size `128`, schema hash `0x6CBEA9DB`, and no `0xA1100024` origin localization/XML fields.

- [ ] **Step 3: Add the Shady Attribute localization and XML origin**

Append this entry to `localization/en_us.json`:

```json
"0xA1100024": "Shady Attribute"
```

Add this field beside `trait_description` in all three trait XML files:

```xml
<T n="trait_origin_description">0xA1100024</T>
```

Keep every existing name, description, icon, age, species, and `GAMEPLAY` value unchanged.

- [ ] **Step 4: Replace the outdated Trait SimData layout**

Change the builder signature to:

```python
def build_trait_simdata(
    table_name, display_name, description, origin_description, icon_instance
):
```

Generate the current `Trait` schema with main-row size `184`, schema hash `0xC8782638`, four tables, and these exact client columns:

```python
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
```

Populate `display_name`, `trait_description`, and `trait_origin_description` as localized-string keys followed by the `0x80000000` sentinel; set `trait_type` to native gameplay value `1`; write the icon as `<QII>(icon_instance, 0x00B2D882, 0)`. Preserve the existing eight age values `(8, 32, 1, 4, 2, 64, 16, 128)` and species value `1` in the list table. Leave optional CAS/filter/display lists empty with the normal `-0x80000000, 0` representation and use the native default `ui_category` pair `(0x80000000, 0xC1A03855)`.

Update all three calls to pass `0xA1100024` between the description key and icon instance:

```python
build_trait_simdata(
    "ShadySimDeals_trait_FamilyAssetLiquidator",
    0xA1100018, 0xA1100019, 0xA1100024, 0x47FFEEDF30C4B115,
)
```

Repeat with the existing Outsourced and Stork name, description, and icon values.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run:

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests/test_build.py -k 'sale_trait_and_buff_simdata or sale_traits_and_moodlets'
```

Expected: PASS with the three Trait resources resolving their name, description, origin, icon, and gameplay type through the current schema.

- [ ] **Step 6: Run full verification and build**

Run:

```powershell
$env:PYTHONPATH='src'; py -3.12 -m pytest -q -p no:cacheprovider tests
py -3.12 build_mod.py
git diff --check
```

Expected: all tests pass, both `dist/ShadySimDeals.ts4script` and `dist/ShadySimDeals.package` build, and `git diff --check` prints nothing.

- [ ] **Step 7: Commit the implementation**

```powershell
git add build_mod.py localization/en_us.json tests/test_build.py tuning/traits
git commit -m "fix: name and categorize sale traits"
```

### Task 2: Install and live acceptance

**Files:**
- Verify: `dist/ShadySimDeals.ts4script`
- Verify: `dist/ShadySimDeals.package`
- Install via: `install_mod.ps1`

**Interfaces:**
- Consumes: verified Task 1 artifacts.
- Produces: installed package for live game validation; no source changes.

- [ ] **Step 1: Confirm The Sims 4 is closed and install**

```powershell
$game = Get-Process TS4_x64 -ErrorAction SilentlyContinue
if ($game) { throw "Close The Sims 4 before installation" }
.\install_mod.ps1
```

- [ ] **Step 2: Verify installed artifact hashes**

```powershell
$installed = 'C:\Users\mauri\Documents\Electronic Arts\The Sims 4\Mods\ShadySimDeals'
foreach ($file in 'ShadySimDeals.ts4script', 'ShadySimDeals.package') {
    $built = (Get-FileHash (Join-Path '.\dist' $file)).Hash
    $copy = (Get-FileHash (Join-Path $installed $file)).Hash
    if ($built -ne $copy) { throw "$file hash mismatch" }
}
```

- [ ] **Step 3: Perform live acceptance tests**

Verify household-member sale, shared unborn sale, and solo unborn sale. For each applicable Sim, open the trait panel and confirm the exact approved trait name, description, and **Shady Attribute** origin label. Confirm moodlets still appear, household transfer/pregnancy termination and payment still complete, and neither `lastUIException.txt` nor a new ShadySimDeals failure log entry is produced.
