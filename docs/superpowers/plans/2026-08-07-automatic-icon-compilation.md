# Automatic Icon Compilation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the normal Python build compile every editable source PNG into a Sims 4-compatible DST5 resource automatically.

**Architecture:** Vendor Microsoft's official x64 `texconv.exe`, use it to generate temporary one-mip BC3/DXT5 DDS files, then perform the small Sims 4 DST5 block shuffle in `build_mod.py`. Package only the in-memory DST5 bytes; remove checked-in compiled textures.

**Tech Stack:** Python 3.12 stdlib, pytest, Microsoft DirectXTex `texconv` may2026 x64, Sims 4 DBPF DST image resources (`0x00B2D882`).

## Global Constraints

- `py -3.12 build_mod.py` must require no separately installed texture application.
- Source icons remain normalized 256x256, 8-bit RGBA PNG files under `icons/`.
- Keep stable resource instances `0xEAA21FFB1081E01A` through `0xEAA21FFB1081E024`.
- Do not modify `src/shady_sim_deals` or any transaction behavior.
- Missing tools, missing images, invalid PNGs, failed conversion, and malformed DDS output must fail clearly.
- Do not commit or push unless the user explicitly requests it.

---

### Task 1: Add and verify the DST5 block transformer

**Files:**
- Modify: `build_mod.py`
- Test: `tests/test_build.py`

**Interfaces:**
- Produces: `dxt5_to_dst5(data: bytes) -> bytes`.
- Consumes: a complete one-mip legacy DDS byte string with `DXT5` FourCC.
- Raises: `ValueError` for a bad signature, non-DXT5 FourCC, dimensions below one, mip count other than one, or an incomplete/extra block body.

- [x] **Step 1: Add a failing exact-layout test**

Add this test using two hand-authored DXT5 blocks so the expected layout is independent of the implementation:

```python
def test_dxt5_to_dst5_groups_block_components_in_sims4_order():
    header = bytearray(128)
    header[:4] = b"DDS "
    struct.pack_into("<II", header, 12, 4, 8)
    struct.pack_into("<I", header, 28, 1)
    header[84:88] = b"DXT5"
    first = bytes(range(16))
    second = bytes(range(16, 32))

    result = build_mod.dxt5_to_dst5(bytes(header) + first + second)

    assert result[:4] == b"DDS "
    assert result[84:88] == b"DST5"
    assert result[128:] == (
        first[0:2] + second[0:2]
        + first[8:12] + second[8:12]
        + first[2:8] + second[2:8]
        + first[12:16] + second[12:16]
    )
```

Add parameterized malformed inputs for bad magic, wrong FourCC, mip count `2`, and a 31-byte body; each must raise `ValueError` with `DDS`, `DXT5`, `one mip`, or `block data` in its message.

- [x] **Step 2: Run the focused test and verify RED**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_build.py -k "dxt5_to_dst5"
```

Expected: FAIL because `build_mod.dxt5_to_dst5` does not exist.

- [x] **Step 3: Implement the minimal transformer**

Add beside the resource constants:

```python
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
```

- [x] **Step 4: Run the focused test and verify GREEN**

Run the command from Step 2. Expected: PASS.

---

### Task 2: Vendor DirectXTex and compile source PNGs

**Files:**
- Create: `tools/directxtex/texconv.exe`
- Create: `tools/directxtex/LICENSE.txt`
- Create: `tools/directxtex/SOURCE.md`
- Modify: `build_mod.py`
- Test: `tests/test_build.py`

**Interfaces:**
- Produces: `TEXCONV_PATH: pathlib.Path`.
- Produces: `validate_icon_png(source: pathlib.Path) -> None`.
- Produces: `compile_icon(source: pathlib.Path, temporary_directory: pathlib.Path, converter: pathlib.Path = TEXCONV_PATH) -> bytes`.
- Consumes: normalized 256x256, bit-depth 8, color-type 6 PNG input.
- Returns: complete 256x256 DST5 bytes.

- [x] **Step 1: Add failing validation and real-conversion tests**

Add tests which:

```python
def test_compile_icon_uses_vendored_converter_and_returns_dst5(tmp_path):
    result = build_mod.compile_icon(
        build_mod.ROOT / "icons/Phone-Computer-App/app-icon.png",
        tmp_path,
    )
    assert result[:4] == b"DDS "
    assert struct.unpack_from("<II", result, 12) == (256, 256)
    assert result[84:88] == b"DST5"


def test_validate_icon_png_rejects_wrong_dimensions(tmp_path):
    source = tmp_path / "bad.png"
    data = bytearray(29)
    data[:8] = b"\x89PNG\r\n\x1a\n"
    struct.pack_into(">II", data, 16, 128, 256)
    data[24:26] = bytes((8, 6))
    source.write_bytes(data)
    with pytest.raises(ValueError, match="256x256"):
        build_mod.validate_icon_png(source)


def test_compile_icon_rejects_missing_converter(tmp_path):
    source = build_mod.ROOT / "icons/Phone-Computer-App/app-icon.png"
    with pytest.raises(FileNotFoundError, match="texconv"):
        build_mod.compile_icon(source, tmp_path, tmp_path / "missing.exe")
```

Also cover a missing source with `FileNotFoundError` and PNG bit depth/color type other than `(8, 6)` with `ValueError("8-bit RGBA")`. For converter failure, write a 29-byte file whose IHDR fields pass validation but whose PNG body is incomplete, run the real vendored converter, and assert `RuntimeError("texconv failed")`.

- [x] **Step 2: Run tests and verify RED**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_build.py -k "compile_icon or validate_icon_png"
```

Expected: FAIL because the compiler interfaces do not exist.

- [x] **Step 3: Vendor the verified official converter and license**

Create `tools/directxtex/`, download the official release binary, and verify it before keeping it:

```powershell
curl.exe -L -o tools\directxtex\texconv.exe https://github.com/microsoft/DirectXTex/releases/download/may2026/texconv.exe
Get-FileHash tools\directxtex\texconv.exe -Algorithm SHA256
```

Expected SHA-256:

```text
DCFDEC10244E02CF5037FBA089C55FB7E1326B1C8181742D77D15FA5CB5EEF06
```

Copy the DirectXTex MIT license text into `LICENSE.txt`. Record project URL, release `may2026`, binary URL, and SHA-256 in `SOURCE.md`.

- [x] **Step 4: Implement PNG validation and conversion**

Set `TEXCONV_PATH = ROOT / "tools" / "directxtex" / "texconv.exe"`. `validate_icon_png` reads only the 29-byte PNG signature/IHDR prefix and checks signature, `(width, height) == (256, 256)`, bit depth `8`, and color type `6`.

Implement `compile_icon` to validate both paths, invoke:

```python
command = (
    str(converter), "-nologo", "-y", "-dx9",
    "-f", "BC3_UNORM", "-m", "1",
    "-o", str(temporary_directory), str(source),
)
result = subprocess.run(command, capture_output=True, text=True)
```

Raise `RuntimeError` containing the source path plus captured stdout/stderr when `returncode != 0`. Read `<temporary_directory>/<source stem>.dds`, pass it to `dxt5_to_dst5`, and return the result.

- [x] **Step 5: Run tests and verify GREEN**

Run the command from Step 2. Expected: all selected tests pass using the vendored executable.

---

### Task 3: Compile all icons during packaging

**Files:**
- Modify: `build_mod.py`
- Modify: `tests/test_build.py`
- Remove: `icons/Compiled/*.dst`

**Interfaces:**
- Changes `ICON_RESOURCES` paths back to the eleven editable PNG files.
- Produces: `compiled_icon_resources() -> tuple[tuple[bytes, int, int, int], ...]`, cached once per Python process.
- Preserves: `package_resources()` output resource keys and all icon instances.

- [x] **Step 1: Change the package test to require source-driven output**

Extend `test_custom_icons_are_packaged_as_dst5_images` to assert `ICON_RESOURCES` contains the exact eleven source PNG paths and that every packaged icon remains a 256x256 DST5 resource. Add:

```python
def test_icon_packaging_does_not_use_checked_in_compiled_assets():
    assert not (build_mod.ROOT / "icons/Compiled").exists()
```

- [x] **Step 2: Remove `icons/Compiled` and verify RED**

Remove only `icons/Compiled/*.dst`, then remove the empty directory. Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_build.py -k "custom_icons or compiled_assets or planned_resource"
```

Expected: FAIL because `package_resources()` still reads removed `.dst` files.

- [x] **Step 3: Wire compilation into `package_resources()`**

Change `ICON_RESOURCES` to the exact source paths and existing instances. Add `from functools import lru_cache`, then:

```python
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
```

Return `resources + compiled_icon_resources()` from `package_resources()`. The cache avoids launching 11 conversion processes for every test call while still recompiling on each new build process.

- [x] **Step 4: Run focused and complete tests**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests/test_build.py
py -3.12 -m pytest -q -p no:cacheprovider tests
```

Expected: all tests pass.

---

### Task 4: Align documentation, build, and install

**Files:**
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`
- Modify: `DEVELOPMENT.md`
- Modify: `SPECS_CHECKLIST.md`
- Modify: `docs/superpowers/specs/2026-08-06-custom-icons-design.md`
- Modify: `docs/superpowers/plans/2026-08-06-custom-icons.md`

**Interfaces:**
- Documents: edit PNG, run normal build, receive rebuilt DST5 resources automatically.
- Preserves: live visual verification remains checked because the DST5 rendering has already passed in game.

- [x] **Step 1: Update maintained documentation**

Document the vendored DirectXTex version/license, automatic conversion, source PNG requirements, build failures, and removal of `icons/Compiled`. Replace every instruction that requires manual DST regeneration.

- [x] **Step 2: Run final verification**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests
py -3.12 build_mod.py
git diff --check
git diff --quiet -- src/shady_sim_deals
```

Expected: all tests pass, both artifacts build, whitespace validation is clean, and runtime source is unchanged.

- [x] **Step 3: Install and verify exact artifacts**

With The Sims 4 closed, run `./install_mod.ps1`. Compare SHA-256 hashes for both files in `dist/` and `Documents/Electronic Arts/The Sims 4/Mods/ShadySimDeals`; each source/destination pair must match.

- [x] **Step 4: Leave changes uncommitted**

Run `git status --short --branch` and report the complete verification evidence. Do not stage, commit, or push.
