# Automatic Icon Compilation Design

## Goal

Make `py -3.12 build_mod.py` rebuild all eleven Sims 4 icon resources directly from the editable PNG files under `icons/`. Replacing a source PNG and running the normal build must be sufficient; no manual conversion step or separately installed application is required.

## Build pipeline

Vendor Microsoft's official x64 `texconv.exe` under `tools/directxtex/` together with the DirectXTex MIT license and source/version attribution. The project is already built and installed through Windows tooling, so a repository-managed Windows executable adds no new platform requirement.

`build_mod.py` keeps the existing source-PNG-to-resource-instance mapping. For each icon it:

1. validates that the PNG exists and is 256x256 RGBA;
2. invokes the vendored converter in a temporary directory to produce one-mip BC3/DXT5 DDS data using a legacy DX9 header;
3. validates the DDS signature, dimensions, DXT5 FourCC, and complete 16-byte block layout;
4. rearranges the DXT5 block components into Sims 4 DST5 order in memory and changes the FourCC to `DST5`;
5. packages the result as resource type `0x00B2D882`, group `0`, using the existing stable instance.

Temporary DDS files are discarded automatically. `icons/Compiled/` is removed because builds no longer consume checked-in generated textures.

## Failure handling

The build fails before writing final artifacts when:

- the vendored converter or a source PNG is missing;
- a source image is not 256x256 RGBA;
- conversion returns a nonzero exit code;
- output is missing or is not a supported single-level DXT5 DDS;
- the DDS body is incomplete.

Errors identify the affected source icon and reason. Existing build artifacts are replaced only after resource construction succeeds, preserving the current build behavior.

## Scope

This changes only development-time image compilation, packaging tests, generated assets, and documentation. Icon resource instances, tuning references, SimData references, runtime Python, pricing, filtering, routing, durations, transfers, payments, and consequences remain unchanged.

## Verification

Automated tests cover:

- a hand-checked DXT5 block fixture transformed into the exact DST5 region order;
- all eleven source PNGs producing 256x256 `DDS` resources with `DST5` FourCC;
- all resource keys, XML references, and SimData references remaining exact;
- a missing converter, missing source, invalid source dimensions, conversion failure, and malformed DDS failing clearly;
- the complete existing regression suite and production build.

Final verification also confirms `icons/Compiled/` is absent, `src/shady_sim_deals` is unchanged, and the rebuilt installed files match the `dist/` artifacts.
