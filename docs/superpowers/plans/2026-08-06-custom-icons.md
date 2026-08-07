# Custom Icons Implementation Plan

> **Historical note (2026-08-07):** This implementation plan is retained as a development record. Its unchecked boxes describe the original workflow, not current repository status; use [`SPECS_CHECKLIST.md`](../../../SPECS_CHECKLIST.md) for current status.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package and display the eleven supplied ShadySimDeals icons across the app category, sale actions, rabbit-hole queue actions, traits, and moodlets without changing transaction behavior.

**Architecture:** Extend the existing DBPF builder with stable BC3/DST5 resources compiled from the supplied PNGs and point the existing XML and generated SimData resource keys at them. Keep the change entirely in assets, build metadata, tuning, tests, and documentation; runtime Python remains untouched.

**Tech Stack:** Python 3.12 build/tests, Python stdlib `struct` and `xml.etree.ElementTree`, Sims 4 DBPF BC3/DST5 resources (`0x00B2D882`), XML tuning, and generated SimData.

## Global Constraints

- This is a presentation-only change; do not modify `src/shady_sim_deals`.
- Preserve picker filtering, pricing, routing, rabbit-hole timing, transfers, payments, and consequences.
- Compile the normalized 256×256 RGBA PNG sources automatically during the normal build.
- Use stable instances `0xEAA21FFB1081E01A` through `0xEAA21FFB1081E024` exactly as assigned in the approved design.
- Do not add dependencies.
- Do not commit or push unless explicitly instructed.

---

### Task 1: Package custom DST5 resources and update SimData keys

**Files:**
- Modify: `build_mod.py:10-30, 59-285, 300-535`
- Modify: `tests/test_build.py:1-150, 475-520`
- Include: `icons/**/*.png`, `tools/directxtex/*`

**Interfaces:**
- Produces: `DST_IMAGE_TYPE = 0x00B2D882`.
- Produces: `ICON_RESOURCES`, a tuple of `(relative_path: str, instance: int)` pairs.
- Preserves: `package_resources()`, returning the complete tuple of `(data, resource_type, group, instance)` resource tuples.
- Uses packaged `DST_IMAGE_TYPE` keys in generated category, Trait, and Buff SimData.

- [x] **Step 1: Add failing package-resource and SimData assertions**

Extend `EXPECTED_RESOURCE_KEYS` with:

```python
{
    (0x00B2D882, 0, instance)
    for instance in range(0xEAA21FFB1081E01A, 0xEAA21FFB1081E025)
}
```

Add a test that verifies the resource type, dimensions, DST5 encoding, and instances:

```python
def test_custom_icons_are_packaged_as_dst5_images():
    expected = set(range(0xEAA21FFB1081E01A, 0xEAA21FFB1081E025))
    packaged = {
        instance: data
        for data, resource_type, group, instance in build_mod.package_resources()
        if resource_type == 0x00B2D882 and group == 0
    }

    assert set(packaged) == expected
    for data in packaged.values():
        assert data[:4] == b"DDS "
        assert struct.unpack_from("<II", data, 12) == (256, 256)
        assert data[84:88] == b"DST5"
```

Update the existing Trait, Buff, and category SimData expectations to the new icon instances and assert each resource-key type equals `0x00B2D882`.

- [x] **Step 2: Run the focused tests and verify RED**

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_build.py -k "custom_icons or simdata or planned_resource"
```

Expected: FAIL because no custom DST5 resources are packaged and SimData still references the previous image resources.

- [x] **Step 3: Add stable image constants and package the assets**

Add beside the existing resource constants:

```python
DST_IMAGE_TYPE = 0x00B2D882
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
```

Compile the mapped PNGs to temporary DST5 bytes, then return the existing resources plus those DST entries. The final implementation is specified in `2026-08-07-automatic-icon-compilation.md`.

```python
return resources + compiled_icon_resources()
```

Missing source files or the vendored converter deliberately raise `FileNotFoundError` and fail the build.

- [x] **Step 4: Point generated SimData at custom DST resources**

Use `DST_IMAGE_TYPE` in `build_pie_menu_category_simdata`, `build_trait_simdata`, and `build_buff_simdata`. Update their call-site icon instances to:

```python
category: 0xEAA21FFB1081E01A
traits:   0xEAA21FFB1081E01F, 0xEAA21FFB1081E020, 0xEAA21FFB1081E021
buffs:    0xEAA21FFB1081E022, 0xEAA21FFB1081E023, 0xEAA21FFB1081E024
```

- [x] **Step 5: Run focused tests and verify GREEN**

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_build.py -k "custom_icons or simdata or planned_resource"
```

Expected: PASS.

---

### Task 2: Reference custom icons from all presentation tuning

**Files:**
- Modify: `tuning/categories/shady_sim_deals_phone.xml`
- Modify: `tuning/interactions/phone_sell_household_member.xml`
- Modify: `tuning/interactions/phone_sell_unborn_nooboo.xml`
- Modify: `tuning/interactions/computer_sell_household_member.xml`
- Modify: `tuning/interactions/computer_sell_unborn_nooboo.xml`
- Modify: `tuning/interactions/household_rabbit_hole_75.xml`
- Modify: `tuning/interactions/household_rabbit_hole_90.xml`
- Modify: `tuning/interactions/household_rabbit_hole_120.xml`
- Modify: `tuning/interactions/unborn_rabbit_hole_90.xml`
- Modify: `tuning/interactions/unborn_rabbit_hole_120.xml`
- Modify: `tuning/interactions/unborn_rabbit_hole_150.xml`
- Modify: `tuning/traits/*.xml`
- Modify: `tuning/buffs/*.xml`
- Modify: `tests/test_build.py`
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`
- Modify: `DEVELOPMENT.md`
- Modify: `SPECS_CHECKLIST.md`

**Interfaces:**
- Consumes: the eleven packaged DST instances from Task 1.
- Produces: `_icon` resource-key tuning for interaction-queue artwork.
- Produces: `pie_menu_icon` resource-key tuning for both phone and computer sale actions.
- Preserves: all non-icon XML nodes and all runtime behavior.

- [x] **Step 1: Add failing exact-reference tests**

Add an XML helper:

```python
def icon_instance(node):
    return int(node.text.rsplit(":", 1)[1], 16)
```

Add a test with the exact interaction mappings:

```python
def test_sale_interactions_use_custom_queue_and_pie_menu_icons():
    interactions = packaged_interactions()
    expected = {
        0xEAA1200000000001: 0xEAA21FFB1081E01B,
        0xEAA21FFB1081E002: 0xEAA21FFB1081E01C,
        0xEAA21FFB1081E003: 0xEAA21FFB1081E01B,
        0xEAA21FFB1081E004: 0xEAA21FFB1081E01C,
        0xEAA21FFB1081E008: 0xEAA21FFB1081E01D,
        0xEAA21FFB1081E009: 0xEAA21FFB1081E01D,
        0xEAA21FFB1081E00A: 0xEAA21FFB1081E01D,
        0xEAA21FFB1081E011: 0xEAA21FFB1081E01E,
        0xEAA21FFB1081E012: 0xEAA21FFB1081E01E,
        0xEAA21FFB1081E013: 0xEAA21FFB1081E01E,
    }
    for instance, expected_icon in expected.items():
        xml = interactions[instance]
        queue_icon = xml.find("./V[@n='_icon']/U/T[@n='key']")
        assert icon_instance(queue_icon) == expected_icon
        pie_icon = xml.find(
            "./V[@n='pie_menu_icon']/V[@n='enabled']/U/T[@n='key']"
        )
        if instance in {
            0xEAA1200000000001,
            0xEAA21FFB1081E002,
            0xEAA21FFB1081E003,
            0xEAA21FFB1081E004,
        }:
            assert icon_instance(pie_icon) == expected_icon
        else:
            assert pie_icon is None
```

Extend existing category, trait, and buff tests to assert their XML icon instances match `0x01A`, `0x01F`–`0x021`, and `0x022`–`0x024` respectively.

- [x] **Step 2: Run the exact-reference tests and verify RED**

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_build.py -k "custom_queue or custom_icons or custom_category or visible_localized"
```

Expected: FAIL because tuning still references base-game icons or has no interaction icon nodes.

- [x] **Step 3: Add entry-action queue and pie-menu icons**

Add this `_icon` shape to each of the four entry interactions, using instance `01B` for household actions and `01C` for unborn actions:

```xml
<V n="_icon" t="resource_key"><U n="resource_key"><T n="key">00b2d882:00000000:eaa21ffb1081e01b</T></U></V>
```

Add the matching pie-menu shape:

```xml
<V n="pie_menu_icon" t="enabled"><V n="enabled" t="resource_key"><U n="resource_key"><T n="key">00b2d882:00000000:eaa21ffb1081e01b</T></U></V></V>
```

Use `eaa21ffb1081e01c` in both nodes for unborn actions.

- [x] **Step 4: Add rabbit-hole queue icons**

Add `_icon` resource-key nodes using `eaa21ffb1081e01d` to the three household duration interactions and `eaa21ffb1081e01e` to the three unborn duration interactions. Do not add `pie_menu_icon`; these interactions are never player-facing pie-menu choices.

- [x] **Step 5: Replace category, trait, and buff icon references**

Update XML references exactly:

```text
category: 0xEAA21FFB1081E01A
traits:   0xEAA21FFB1081E01F, 0xEAA21FFB1081E020, 0xEAA21FFB1081E021
buffs:    0xEAA21FFB1081E022, 0xEAA21FFB1081E023, 0xEAA21FFB1081E024
```

All references use type `00b2d882` and group `00000000`.

- [x] **Step 6: Run build tests and verify GREEN**

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_build.py
```

Expected: PASS.

- [x] **Step 7: Align maintained documentation**

Document the eleven packaged custom DST5 resources and their visual-only scope in `README.md`, `ARCHITECTURE.md`, and `DEVELOPMENT.md`. Add automated-complete and live-pending icon verification entries to `SPECS_CHECKLIST.md`.

- [x] **Step 8: Run final verification and build**

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests
py -3.12 build_mod.py
git diff --check
git status --short --branch
```

Expected: all tests pass, both artifacts build, whitespace validation is clean, `src/shady_sim_deals` has no changes, and only the icon assets plus intended build, tuning, test, spec, plan, and documentation files are uncommitted.
